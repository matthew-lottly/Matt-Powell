# Tools Brainstorm: Building with 86 Spatial Equations

## Overview
This document outlines potential tools and applications that leverage the 86 spatial analysis equations now available in geoprompt. These tools span multiple domains and use cases: analysis, optimization, prediction, classification, and visualization.

**Total Equations Available: 86**
- Distance metrics: 2 (euclidean, haversine)
- Core decay/interaction functions: 16
- 40 custom spatial functions (previous expansion)
- 32 domain-specific functions (latest expansion)

---

## Category 1: Analysis Tools
*Compute and measure spatial metrics on regions/networks*

### 1.1 Epidemiology Analysis Suite
**`EpidemicSpatialAnalyzer`** - Analyze disease transmission and vulnerability
- **Uses**: `transmission_risk_score`, `incidence_rate_decay`, `vaccination_protection_score`, `immunity_barrier_score`, `gravity_interaction`
- **Inputs**: Population locations, disease prevalence, vaccination rates, travel patterns
- **Outputs**: Risk maps, herd immunity regions, transmission corridors
- **UI**: Heat maps showing transmission risk; vaccination gap identification
- **Business Case**: Public health agencies, CDC, epidemiologists

**`OutbreakTrajectoryModeler`** - Model disease spread progression
- **Uses**: `incidence_rate_decay`, `exponential_decay`, `transmission_risk_score`
- **Inputs**: Index case location, historical spread data, environmental factors
- **Outputs**: Predicted affected areas over time, critical intervention zones
- **Use Case**: Early warning for pandemic preparedness

### 1.2 Urban Planning Analysis Suite
**`AccessibilityAnalyzer`** - Measure pedestrian/transit accessibility
- **Uses**: `walkability_score`, `transit_accessibility_score`, `land_value_gradient`, `mixed_use_score`
- **Inputs**: Sidewalk data, intersection density, transit stops, amenities
- **Outputs**: Walkability index, accessibility equity maps, gentrification risk zones
- **UI**: Grade-based accessibility ratings by neighborhood, equity overlays
- **Business Case**: City planners, real estate analysts, transit agencies

**`LandUseOptimizer`** - Recommend optimal mixed-use development
- **Uses**: `mixed_use_score`, `gentrification_pressure_index`, `land_value_gradient`, `accessibility_potential`
- **Inputs**: Current land use distribution, property values, population demographics
- **Outputs**: Recommended zoning changes, development priorities, equity impact
- **Impact**: Reduce sprawl, promote walkable neighborhoods

**`GentrificationRiskMonitor`** - Identify and track gentrification pressure
- **Uses**: `gentrification_pressure_index`, `land_value_gradient`, `temporal_stability_score`
- **Inputs**: Property appreciation rates, income changes, demographic shifts
- **Outputs**: Risk zones, vulnerable populations, intervention points
- **Use Case**: Community organizations, housing advocacy

### 1.3 Transportation Analysis Suite
**`TrafficFlowAnalyzer`** - Real-time network traffic assessment
- **Uses**: `traffic_congestion_index`, `congestion_penalized_interaction`, `route_efficiency_score`
- **Inputs**: Current flow rates, road capacity, vehicle counts
- **Outputs**: Congestion hot spots, bottleneck identification, incident impact zones
- **Integration**: Real-time GPS, traffic sensors, incident reports

**`MultimodalAccessibilityAssessment`** - Compare transportation mode access
- **Uses**: `transit_accessibility_score`, `parking_availability_factor`, `mode_share_incentive`, `traffic_congestion_index`
- **Inputs**: Roads, transit, bike paths, parking inventories
- **Outputs**: Accessibility gaps by mode, incentives for mode shift, equity analysis
- **Business Case**: DOT, traffic engineers, city planners

**`LogisticsNetworkOptimizer`** - Optimize delivery routes and depots
- **Uses**: `route_efficiency_score`, `path_detour_penalty`, `anisotropic_friction_cost`, `accessibility_potential`
- **Inputs**: Road network, terrain, vehicle types, demand locations
- **Outputs**: Optimal depot locations, efficient routes, cost projections
- **Use Case**: Amazon, UPS, FedEx supply chain planning

### 1.4 Environmental Analysis Suite
**`PollutionDispersionMapper`** - Map air/water pollution spread
- **Uses**: `pollution_dispersion_model`, `gaussian_decay`, `exponential_decay`
- **Inputs**: Emission sources, wind patterns, water currents, environmental conditions
- **Outputs**: Pollution concentration maps, population exposure, compliance zones
- **Integration**: Weather data, point source emissions, water quality sensors
- **Business Case**: EPA, state environmental agencies

**`HabitatFragmentationAssessment`** - Analyze wildlife connectivity
- **Uses**: `habitat_fragmentation_score`, `network_redundancy_gain`, `connectivity_index`, `spatial_index`
- **Inputs**: Protected areas, land use, roads/barriers, species movement data
- **Outputs**: Fragmentation scores, connectivity bottlenecks, corridor priorities
- **Use Case**: Conservation organizations, wildlife management

**`ClimateVulnerabilityAssessment`** - Identify climate change hotspots
- **Uses**: `climate_vulnerability_index`, `green_space_benefits_radius`, `environmental_limit`
- **Inputs**: Exposure hazards (floods, heat), population sensitivity, adaptive capacity
- **Outputs**: Vulnerability maps, priority intervention zones, benefits of green infrastructure
- **Use Case**: FEMA, climate adaptation planners, insurance companies

**`EcosystemServicesMapper`** - Quantify nature-based benefits
- **Uses**: `green_space_benefits_radius`, `habitat_fragmentation_score`, `multi_scale_accessibility_score`
- **Inputs**: Parks, forests, wetlands, urban green space
- **Outputs**: Cooling benefits, air quality benefits, recreation access maps
- **Impact**: Value ecosystem services for planning decisions

### 1.5 Population & Demographics Analysis
**`DemographicProjector`** - Project population changes
- **Uses**: `migration_attraction_index`, `birth_rate_modifier`, `mortality_risk_index`, `population_carrying_capacity`
- **Inputs**: Current demographics, economic trends, migration patterns, healthcare quality
- **Outputs**: Population projections, natural increase/decrease, migration flows
- **Use Case**: Census Bureau, regional planners

**`HealthEquityAnalyzer`** - Assess health disparities across regions
- **Uses**: `mortality_risk_index`, `healthcare_access`, `disease_burden`, `environmental_hazard`
- **Inputs**: Health outcomes, provider locations, environmental exposures, demographic data
- **Outputs**: Health equity maps, disparity hotspots, intervention targets
- **Business Case**: Health departments, CMS, hospital systems

### 1.6 Economic Analysis Suite
**`MarketCompetitionAnalyzer`** - Analyze regional market structure
- **Uses**: `market_concentration_index`, `competitive_influence`, `business_cluster_advantage`
- **Inputs**: Firm locations, market shares, business types
- **Outputs**: Market concentration maps, competitive dynamics, cluster identification
- **Use Case**: Antitrust agencies, economic development organizations

**`TradeFlowAnalyzer`** - Map economic exchange networks
- **Uses**: `trade_flow_intensity`, `gravity_interaction`, `distance_decay`
- **Inputs**: Ports, borders, trade agreements, distance
- **Outputs**: Trade corridors, bilateral intensity maps, bottleneck identification
- **Use Case**: Commerce Department, international economists

**`EconomicClusterMapper`** - Identify and assess business clusters
- **Uses**: `business_cluster_advantage`, `market_concentration_index`, `accessibility_potential`
- **Inputs**: Business locations, employment data, industry classification
- **Outputs**: Cluster identification, agglomeration benefits, growth potential
- **Impact**: Economic development strategy

**`ConsumerPowerAnalyzer`** - Assess local purchasing capacity
- **Uses**: `consumer_purchasing_power`, `land_value_gradient`, `employment_rate`
- **Inputs**: Income distribution, employment data, cost of living
- **Outputs**: Local spending capacity maps, market opportunity zones
- **Business Case**: Retailers, franchisors, market researchers

### 1.7 Social Network Analysis Suite
**`InformationDiffusionTracker`** - Monitor information/innovation spread
- **Uses**: `information_diffusion_rate`, `network_centrality_influence`, `community_cohesion_score`
- **Inputs**: Network structure, seed adopters, virality factors
- **Outputs**: Diffusion progression, influence maps, adoption forecasts
- **Use Case**: Marketing, public health campaigns, social scientists

**`CommunityCoherenceAnalyzer`** - Measure social capital and cohesion
- **Uses**: `community_cohesion_score`, `cultural_similarity_index`, `network_centrality_influence`
- **Inputs**: Social ties (from surveys/networks), cultural data
- **Outputs**: Cohesion scores by community, bridge communities, integration needs
- **Use Case**: Sociologists, community developers

**`CulturalCompatibilityAssessment`** - Assess cultural fit for integration
- **Uses**: `cultural_similarity_index`, `community_cohesion_score`
- **Inputs**: Cultural attributes, value alignment, language similarity, shared history
- **Outputs**: Compatibility scores, integration roadmaps, friction points
- **Use Case**: Immigration policy, international development, business mergers

### 1.8 Acoustic & Visibility Analysis
**`NoiseImpactMapper`** - Map noise pollution exposure
- **Uses**: `noise_propagation_level`, `acoustic_reverberation_index`
- **Inputs**: Noise sources (airports, highways, industry), distance, atmospheric conditions
- **Outputs**: Noise level maps, affected populations, noise-sensitive area identification
- **Use Case**: EPA, FAA, urban planners, real estate assessment

**`VisibilityAnalyzer`** - Analyze landmark prominence and visibility
- **Uses**: `visual_prominence_score`, `sky_view_factor`, `directional_alignment`
- **Inputs**: Building heights, density, landmarks, viewpoints
- **Outputs**: Visibility maps, landmark impact, view corridor preservation
- **Use Case**: Urban designers, historic preserve, tourism

**`SkyAccessAnalyzer`** - Assess urban canyon effects
- **Uses**: `sky_view_factor`, `visual_prominence_score`
- **Inputs**: Building heights, street widths, density
- **Outputs**: Sky view factors, solar access potential, wind corridors
- **Impact**: Green building assessment, microclimate analysis

---

## Category 2: Optimization Tools
*Find optimal locations, routes, resource allocation*

### 2.1 Location Optimization
**`FacilityLocationOptimizer`** - Find optimal facility placement
- **Uses**: `accessibility_potential`, `gravity_interaction`, `prompt_interaction`, `market_concentration_index`
- **Inputs**: Demand locations/weights, travel costs, existing facilities
- **Outputs**: Optimal location recommendations, service coverage maps, equity metrics
- **Algorithms**: p-median, p-center, coverage models
- **Use Case**: Healthcare, emergency services, retail, warehousing

**`EquitableAccessibilityOptimizer`** - Balance service access across population
- **Uses**: `accessibility_potential`, `coverage_equity_score`, `weighted_local_summary()`
- **Inputs**: Service locations, populations by demographics/ability
- **Outputs**: Allocation that minimizes access inequality
- **Impact**: Reduce health/service disparities

**`GreenerDevelopmentPlanner`** - Optimize green infrastructure placement
- **Uses**: `green_space_benefits_radius`, `habitat_fragmentation_score`, `multi_scale_accessibility_score`
- **Inputs**: Existing green space, urban area, cooling/air quality needs
- **Outputs**: Priority new park locations, connectivity corridors
- **Impact**: Maximize public health benefits per dollar

### 2.2 Resource Allocation Optimization
**`EmergencyResponseAllocator`** - Optimal emergency resource positioning
- **Uses**: `accessibility_potential`, `response_time_decay`, `coverage_equity_score`
- **Inputs**: Call volumes, response time targets, equity considerations
- **Outputs**: Fire station, hospital, police precinct locations
- **Use Case**: Emergency services, disaster preparedness

**`PublicHealthInterventionPlanner`** - Target intervention resources
- **Uses**: `transmission_risk_score`, `mortality_risk_index`, `accessibility_potential`
- **Inputs**: Disease burden, population vulnerability, resource constraints
- **Outputs**: Optimal vaccination/testing site locations
- **Impact**: Maximize lives saved per resource unit

### 2.3 Route Optimization
**`MultimodalRouteOptimizer`** - Find best multimodal journey
- **Uses**: `route_efficiency_score`, `transit_support_score`, `mode_share_incentive`, `path_detour_penalty`
- **Inputs**: Origin, destination, mode preferences, time constraints
- **Outputs**: Optimized route, mode sequence, carbon footprint
- **Use Case**: Transit agencies, trip planning apps

**`EcoFriendlyDeliveryRouter`** - Minimize delivery environmental impact
- **Uses**: `route_efficiency_score`, `traffic_congestion_index`, `anisotropic_friction_cost`
- **Inputs**: Deliveries, vehicle types, time windows, traffic patterns
- **Outputs**: Routes minimizing fuel/emissions, time windows respected
- **Business Case**: Logistics companies, sustainability goals

### 2.4 Development Sequencing
**`EquitableGrowthSequencer`** - Plan development to reduce gentrification
- **Uses**: `gentrification_pressure_index`, `land_value_gradient`, `community_cohesion_score`
- **Inputs**: Properties, development pipeline, community characteristics
- **Outputs**: Development sequencing that preserves community character
- **Impact**: Inclusive development strategy

---

## Category 3: Prediction Tools
*Forecast spatial phenomena and futures*

### 3.1 Disease & Health Prediction
**`EpidemicForecast`** - Predict epidemic trajectory
- **Uses**: `incidence_rate_decay`, `transmission_risk_score`, `gravity_interaction`
- **Inputs**: Current cases, location, population density, behavior changes
- **Outputs**: Case predictions, peak timing, affected areas, hospital surge needs
- **Integration**: Real-time case data, mobility data
- **Use Case**: Public health response

**`MortalityRiskForecast`** - Predict mortality risk by region
- **Uses**: `mortality_risk_index`, `healthcare_access`, `environmental_hazard`
- **Inputs**: Health indicators, healthcare quality, environmental exposures
- **Outputs**: Mortality forecasts, vulnerable populations, intervention needs
- **Use Case**: Public health, insurance

### 3.2 Population & Migration Prediction
**`MigrationFlowForecast`** - Predict population movements
- **Uses**: `migration_attraction_index`, `gravity_interaction`, `distance_decay`
- **Inputs**: Economic opportunity, quality of life, distance, historical patterns
- **Outputs**: Migration flows, destination popularity, population shifts
- **Use Case**: Urban planning, workforce forecasting

**`PopulationGrowthForecast`** - Predict regional population changes
- **Uses**: `birth_rate_modifier`, `mortality_risk_index`, `migration_attraction_index`, `population_carrying_capacity`
- **Inputs**: Demographics, economic trends, environmental limits
- **Outputs**: Population projections, growth rates, carrying capacity exceeded risk
- **Use Case**: Infrastructure planning, resource allocation

### 3.3 Economic Prediction
**`EconomicGrowthForecast`** - Predict regional economic changes
- **Uses**: `business_cluster_advantage`, `market_concentration_index`, `trade_flow_intensity`
- **Inputs**: Business growth, cluster dynamics, trade patterns
- **Outputs**: Growth projections, cluster strength, economic resilience
- **Use Case**: Economic development, investment decisions

**`RealEstatePriceForecaster`** - Predict property value trends
- **Uses**: `land_value_gradient`, `gentrification_pressure_index`, `accessibility_potential`
- **Inputs**: Historical prices, accessibility, demographics, development activity
- **Outputs**: Price forecasts, risk zones, investment opportunities
- **Business Case**: Real estate, appraisal, investment

### 3.4 Innovation Diffusion Prediction
**`TechAdoptionPredictor`** - Forecast technology spread
- **Uses**: `information_diffusion_rate`, `network_centrality_influence`, `cultural_similarity_index`
- **Inputs**: Current adopters, network structure, preference data
- **Outputs**: Adoption timeline, key influencers, lagging regions
- **Use Case**: Tech companies, innovation policy

---

## Category 4: Classification Tools
*Categorize places and identify types*

### 4.1 Urban Classification
**`UrbanTypeClassifier`** - Classify neighborhoods by character
- **Uses**: `mixed_use_score`, `walkability_score`, `land_value_gradient`, `business_cluster_advantage`
- **Inputs**: Land use, pedestrian infrastructure, economic activity
- **Outputs**: Urban types (downtown, suburb, mixed, etc.), characteristics
- **Use Case**: Urban design, zoning

**`InequityZoneIdentifier`** - Identify disadvantaged areas
- **Uses**: `coverage_equity_score`, `accessibility_potential`, `mortality_risk_index`, `consumer_purchasing_power`
- **Inputs**: Services, health outcomes, income, employment, environmental hazards
- **Outputs**: Disadvantage scores, intervention priorities
- **Impact**: Targeted equitable development

### 4.2 Environmental Classification
**`HabitatTypeClassifier`** - Classify habitat quality and connectivity
- **Uses**: `habitat_fragmentation_score`, `network_redundancy_gain`, `landscape_diversity`
- **Inputs**: Land cover, protected areas, species data
- **Outputs**: Habitat types, connectivity status, priority corridors
- **Use Case**: Conservation planning

**`ClimateRiskZoneMap`** - Classify climate vulnerability zones
- **Uses**: `climate_vulnerability_index`, `green_space_benefits_radius`, `population_carrying_capacity`
- **Inputs**: Hazard exposure, population sensitivity, adaptive capacity
- **Outputs**: Risk zones (high/medium/low), priority adaptation areas
- **Use Case**: Climate adaptation, insurance

### 4.3 Social Classification
**`CommunityTypeProfiler`** - Classify community characteristics
- **Uses**: `community_cohesion_score`, `cultural_similarity_index`, `network_centrality_influence`
- **Inputs**: Social ties, cultural heritage, network position
- **Outputs**: Community profiles, fragmentation status, bridge communities
- **Use Case**: Community development, social services

**`AffiliationIdentifier`** - Classify shared group membership
- **Uses**: `cultural_similarity_index`, `community_cohesion_score`
- **Inputs**: Values, practices, identity markers
- **Outputs**: Group affiliations, integration potential, friction areas
- **Use Case**: Sociology research, integration policy

---

## Category 5: Visualization Tools
*Render spatial results and patterns*

### 5.1 Interactive Map Visualization
**`EquityDashboard`** - Interactive equity metric visualization
- **Equations**: All equations aggregated to equity dimensions
- **Features**: Layer by access type, overlay demographics, identify disparities
- **Use Case**: Community engagement, council meetings, grant applications

**`AccessibilityVisualization`** - Interactive accessibility explorer
- **Uses**: All distance-decay equations, accessibility metrics
- **Features**: Explore by mode, distance threshold, demographic filters
- **Use Case**: Transit planning, site selection

**`ClimateVulnerabilityDashboard`** - Interactive climate risk explorer
- **Uses**: `climate_vulnerability_index`, hazard maps, adaptation options
- **Features**: Scenario modeling, intervention comparison, equity overlays
- **Use Case**: Climate adaptation planning, insurance underwriting

### 5.2 Analytical Visualizations
**`heatmaps`** - Spatial density/intensity visualization
- **Equations**: All equations can generate heatmaps (disease, traffic, pollution, opportunity)
- **Features**: Graduated colors, legend, interactive zoom

**`FlowDiagrams`** - Network flow visualization
- **Uses**: `trade_flow_intensity`, `migration_attraction_index`, `information_diffusion_rate`
- **Features**: Arrow size/color by intensity, node sizing by importance
- **Use Case**: Migration, trade, information spread

**`EquitySurfaceMap`** - Smooth accessibility surface with equity overlay
- **Uses**: `multi_scale_accessibility_score`, demographic layers
- **Features**: Reveal disparities through surface color/pattern

### 5.3 Decision Support Visualizations
**`LocationScoreMaps`** - Multi-criteria location suitability
- **Uses**: Multiple equations scored and weighted per criteria
- **Features**: Single suitability layer or multi-criteria interface
- **Use Case**: Site selection, development planning

**`ImpactProjections`** - Show "before/after" spatial changes
- **Uses**: All equations applied to future/alternative scenarios
- **Features**: Side-by-side comparison, metric summaries

---

## Category 6: Research & Specialized Tools
*Advanced analysis for specific research domains*

### 6.1 Epidemiology & Public Health Research
**`SpatialEpidemiologyLab`** - Sophisticated disease model builder
- **Uses**: All epidemiology equations + spatial regression, kriging, network analysis
- **Features**: Hypothesis testing, sensitivity analysis, model comparison
- **Use Case**: Academic epidemiology, disease surveillance

**`HealthGIS`** - Comprehensive health geography system
- **Uses**: All health-related equations for assessment/forecasting
- **Features**: Provider/patient overlay, travel time, equity analysis
- **Integration**: Hospital systems, Medicare data, disease registries

### 6.2 Urban Science Research
**`UrbanScenarioModeler`** - Forecast urban change under alternatives
- **Uses**: All urban planning equations applied to development scenarios
- **Features**: What-if modeling, equity impact assessment
- **Use Case**: Urban research, planning alternatives

**`GentrificationTracker`** - Long-term gentrification monitoring
- **Uses**: `gentrification_pressure_index`, property markets, demographics over time
- **Features**: Historical tracking, early warning system
- **Use Case**: Community organizations, housing advocacy research

### 6.3 Environmental & Climate Research
**`LandscapeEcologyAnalyzer`** - Advanced habitat connectivity assessment
- **Uses**: Fragmentation, connectivity, species movement equations
- **Features**: Population viability analysis, corridor design
- **Use Case**: Conservation genetics, ecological research

**`ClimateAdaptationModeler`** - Co-design adaptation portfolios
- **Uses**: Vulnerability equations + adaptation action scenarios
- **Features**: Portfolio optimization, co-benefits analysis
- **Use Case**: IPCC research, city/regional adaptation planning

### 6.4 Social Science Research
**`NetworkInfluenceAnalyzer`** - Study diffusion mechanisms
- **Uses**: Information diffusion, network centrality, community cohesion equations
- **Features**: Simulation, sensitivity analysis, mechanism testing
- **Use Case**: Sociology, marketing science, behavioral research

**`CulturalGeographyAnalyzer`** - Study cultural similarity and integration
- **Uses**: `cultural_similarity_index`, spatial patterns
- **Features**: Measure cultural landscapes, integration outcomes
- **Use Case**: Cultural geography, immigration research

### 6.5 Economics & Development Research
**`EconomicGeographyLab`** - Study agglomeration and trade
- **Uses**: Cluster, trade flow, competition equations
- **Features**: Model formation dynamics, policy simulations
- **Use Case**: Economic geography, development economics

**`SocialEquityResearchLab`** - Study access inequality drivers
- **Uses**: Multiple equations combined as equity dimensions
- **Features**: Decompose inequality, identify causal factors
- **Use Case**: Sociology, public policy research

---

## Category 7: Integration Platforms
*Systems that combine multiple tool capabilities*

### 7.1 Government & Planning Platforms
**`CityPlus`** - Comprehensive municipal analysis platform
- **Combines**: Accessibility, equity, climate, growth, economic tools
- **Use Case**: City planning departments, budget/zoning decisions
- **Scale**: Municipal

**`RegionalGIS`** - Multi-county/state planning system
- **Combines**: All tools with regional aggregation
- **Use Case**: MPOs, state agencies, economic development
- **Scale**: Regional (5-50 counties)

### 7.2 Industry Platforms
**`LogisticsOptimizer+`** - Supply chain intelligence platform
- **Combines**: Location, routing, market analysis tools
- **Use Case**: Retail, e-commerce, logistics companies
- **Integration**: Real-time demand, traffic, workforce data

**`HealthEquityHub`** - Healthcare system analysis/planning
- **Combines**: Access, health equity, population health tools
- **Use Case**: Healthcare systems, insurance companies, Medicare
- **Integration**: Claims data, provider directories, health records

**`EconomicDevelopmentExchange`** - Regional development platform
- **Combines**: Market analysis, business clusters, growth forecast tools
- **Use Case**: Economic development organizations, Chambers of Commerce
- **Integration**: Business registries, labor stats, trade data

### 7.3 Research Platforms
**`SpatialAnalyticsLab`** - Full research-grade analysis system
- **Combines**: All analysis, optimization, prediction, research tools
- **Use Case**: Universities, research institutions, think tanks
- **Features**: API, batch processing, advanced statistics

---

## Phase 1: MVP Tools (Focus First)
*Start here - highest demand, broadest impact*

1. **AccessibilityAnalyzer** - Foundational, high community impact
2. **EquitableAccessibilityOptimizer** - Directly applies equity focus
3. **TrafficFlowAnalyzer** - Immediate practical value
4. **PollutionDispersionMapper** - Environmental demand growing
5. **FacilityLocationOptimizer** - Broad application across sectors
6. **OutbreakTrajectoryModeler** - Pandemic prep ongoing demand
7. **EpidemicForecast** - Public health priority
8. **MarketCompetitionAnalyzer** - Economic development need

---

## Phase 2: Expansion Tools (Next Priority)
*Build on MVP success*

- Location optimization suite (sector-specific)
- Population/migration prediction tools
- Urban classification tools
- More specialized industry tools

---

## Technology Notes
- **Backend**: All tools leverage geoprompt's spatial_index, frame.py for efficiency
- **Performance Strategy**: Reference existing perf docs for small/medium/large dataset handling
- **API Layer**: Expose as REST endpoints or CLI commands
- **UI/Frontend**: Web dashboards (Streamlit, Plotly, Folium for maps)
- **Data Integration**: Connect to open data sources (census, weather, traffic, etc.)

---

## Repository Organization
- `geoprompt/` - Core equation library (complete: 86 equations)
- `tools/` - New directory for tool implementations
  - `tools/epidemiology/` - Disease analysis tools
  - `tools/urban/` - Urban planning tools
  - `tools/transportation/` - Traffic/routing tools
  - `tools/environment/` - Pollution/climate tools
  - `tools/economic/` - Market/business tools
  - `tools/social/` - Community/network tools
  - `tools/visualization/` - Mapping/dashboards
- `strata/` - Could house research tools, data platforms

---

## Next Steps
1. Select 3-4 MVP tools to build
2. Create tool specifications for chosen tools
3. Implement tool infrastructure (CLI, API, UI template)
4. Build first tool end-to-end as reference implementation
5. Scale to other tools using template
