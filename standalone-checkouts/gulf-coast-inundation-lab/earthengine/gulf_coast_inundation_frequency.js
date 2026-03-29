var CONFIG = {
  startDate: '1982-01-01',
  endDate: '2021-12-31',
  huc2Codes: ['03', '08', '12'],
  maxCloudCover: 10,
  aweiThreshold: -0.00014,
  minObservationCount: 20,
  leafOffOnly: false,
  exportToDrive: false,
  exportDescription: 'gulf_coast_inundation_frequency',
  exportFolder: 'gee-gulf-coast',
  exportFilePrefix: 'gulf_coast_inundation_frequency'
};

var HUC06 = ee.FeatureCollection('USGS/WBD/2017/HUC06');
var JRC_OCCURRENCE = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence');

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

  var december = ee.Filter.calendarRange(12, 12, 'month');
  var januaryToApril = ee.Filter.calendarRange(1, 4, 'month');
  return collection.filter(ee.Filter.or(december, januaryToApril));
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
var water = collection.select('water');
var observationCount = water.count().rename('observationCount');
var inundationFrequency = water.sum()
  .divide(observationCount)
  .multiply(100)
  .rename('inundationFrequency');
var permanentWater = JRC_OCCURRENCE.gte(90).rename('permanentWater');
var episodicInundation = inundationFrequency
  .updateMask(permanentWater.not())
  .rename('episodicInundation');
var reliableEpisodic = episodicInundation
  .updateMask(observationCount.gte(CONFIG.minObservationCount))
  .rename('reliableEpisodicInundation');
var exportImage = ee.Image.cat([
  inundationFrequency,
  reliableEpisodic,
  observationCount
]).clip(studyArea);

Map.centerObject(studyArea, 6);
Map.addLayer(reliableEpisodic, {
  min: 0,
  max: 60,
  palette: ['#f7f4ea', '#d9e3d7', '#77b8af', '#1d8b8a', '#d4573f']
}, 'Episodic inundation frequency (%)');
Map.addLayer(observationCount, {
  min: 0,
  max: 200,
  palette: ['#f7f4ea', '#c9d3cb', '#78908a', '#173642']
}, 'Observation support');
Map.addLayer(permanentWater.selfMask(), {palette: ['#225ea8']}, 'Near-permanent water');

print('Study area', studyArea);
print('Image count', collection.size());
print('Date range', CONFIG.startDate + ' to ' + CONFIG.endDate);
print('Cloud threshold', CONFIG.maxCloudCover);
print('AWEIsh threshold', CONFIG.aweiThreshold);

if (CONFIG.exportToDrive) {
  Export.image.toDrive({
    image: exportImage,
    description: CONFIG.exportDescription,
    folder: CONFIG.exportFolder,
    fileNamePrefix: CONFIG.exportFilePrefix,
    region: studyArea,
    scale: 30,
    crs: 'EPSG:5070',
    maxPixels: 1e13
  });
}