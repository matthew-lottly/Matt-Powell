var CONFIG = {
  startDate: '1982-01-01',
  endDate: '2021-12-31',
  huc2Codes: ['03', '08', '12'],
  maxCloudCover: 10,
  aweiThreshold: -0.00014,
  leafOffOnly: false,
  validationAssetId: 'users/your-username/gulf_coast_validation_aois',
  exportDescription: 'gulf_coast_gauge_validation_export',
  exportFolder: 'gee-gulf-coast',
  exportFilePrefix: 'gulf_coast_gauge_validation'
};

// Upload data/gauge_validation_manifest.geojson as a table asset and point
// validationAssetId at that uploaded collection before running this export.

var HUC06 = ee.FeatureCollection('USGS/WBD/2017/HUC06');

function buildStudyArea() {
  return HUC06
    .filter(ee.Filter.inList('huc2', CONFIG.huc2Codes))
    .geometry()
    .dissolve();
}

function qaMask(image) {
  var qa = image.select('QA_PIXEL');
  var mask = qa.bitwiseAnd(1 << 1).eq(0)
    .and(qa.bitwiseAnd(1 << 2).eq(0))
    .and(qa.bitwiseAnd(1 << 3).eq(0))
    .and(qa.bitwiseAnd(1 << 4).eq(0))
    .and(qa.bitwiseAnd(1 << 5).eq(0));
  return image.updateMask(mask);
}

function prepTmEtm(image) {
  var optical = image.select(
    ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7'],
    ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
  ).multiply(0.0000275).add(-0.2);
  return optical.addBands(image.select('QA_PIXEL'))
    .copyProperties(image, image.propertyNames());
}

function prepOli(image) {
  var optical = image.select(
    ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'],
    ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
  ).multiply(0.0000275).add(-0.2);
  return optical.addBands(image.select('QA_PIXEL'))
    .copyProperties(image, image.propertyNames());
}

function addWaterBands(image) {
  var awei = image.expression(
    'blue + 2.5 * green - 1.5 * (nir + swir1) - 0.25 * swir2',
    {
      blue: image.select('blue'),
      green: image.select('green'),
      nir: image.select('nir'),
      swir1: image.select('swir1'),
      swir2: image.select('swir2')
    }
  ).rename('aweish');
  var water = awei.gt(CONFIG.aweiThreshold).rename('water');
  return image.addBands([awei, water]);
}

function maybeLeafOff(collection) {
  if (!CONFIG.leafOffOnly) {
    return collection;
  }

  var winter = ee.Filter.calendarRange(12, 12, 'month');
  var spring = ee.Filter.calendarRange(1, 4, 'month');
  return collection.filter(ee.Filter.or(winter, spring));
}

function buildCollection(studyArea) {
  var common = function(collectionId, prepFn) {
    return ee.ImageCollection(collectionId)
      .filterBounds(studyArea)
      .filterDate(CONFIG.startDate, CONFIG.endDate)
      .filter(ee.Filter.lte('CLOUD_COVER', CONFIG.maxCloudCover))
      .map(prepFn);
  };

  var collection = common('LANDSAT/LT04/C02/T1_L2', prepTmEtm)
    .merge(common('LANDSAT/LT05/C02/T1_L2', prepTmEtm))
    .merge(common('LANDSAT/LE07/C02/T1_L2', prepTmEtm))
    .merge(common('LANDSAT/LC08/C02/T1_L2', prepOli))
    .merge(common('LANDSAT/LC09/C02/T1_L2', prepOli))
    .map(qaMask)
    .map(addWaterBands);

  return maybeLeafOff(collection).sort('system:time_start');
}

var studyArea = buildStudyArea();
var collection = buildCollection(studyArea);
var validationAois = ee.FeatureCollection(CONFIG.validationAssetId);
var pixelArea = ee.Image.pixelArea().rename('pixelArea');

function summarizeImage(image) {
  var sceneDate = image.date().format('YYYY-MM-dd');
  var waterArea = pixelArea.updateMask(image.select('water'));

  return validationAois.map(function(feature) {
    var geometry = feature.geometry();
    var inundatedArea = ee.Number(waterArea.reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: geometry,
      scale: 30,
      maxPixels: 1e10,
      tileScale: 4
    }).get('pixelArea', 0));
    var totalArea = ee.Number(pixelArea.reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: geometry,
      scale: 30,
      maxPixels: 1e10,
      tileScale: 4
    }).get('pixelArea', 0));
    var percentInundated = ee.Algorithms.If(
      totalArea.gt(0),
      inundatedArea.divide(totalArea).multiply(100),
      null
    );

    return ee.Feature(null, {
      gaugeId: feature.get('gaugeId'),
      gaugeName: feature.get('gaugeName'),
      date: sceneDate,
      imageId: image.get('LANDSAT_PRODUCT_ID'),
      cloudCover: image.get('CLOUD_COVER'),
      inundatedAreaSqM: inundatedArea,
      percentInundated: percentInundated
    });
  });
}

var validationTable = ee.FeatureCollection(collection.map(summarizeImage).flatten());

print('Validation AOI count', validationAois.size());
print('Validation export rows', validationTable.size());

Map.centerObject(studyArea, 6);
Map.addLayer(validationAois, {color: '#d4573f'}, 'Validation AOIs');

Export.table.toDrive({
  collection: validationTable,
  description: CONFIG.exportDescription,
  folder: CONFIG.exportFolder,
  fileNamePrefix: CONFIG.exportFilePrefix,
  fileFormat: 'CSV'
});