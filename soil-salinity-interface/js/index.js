// elements that make up the popup
const container = document.getElementById("popup");
const content = document.getElementById("popup-content");
const closer = document.getElementById("popup-closer");

// create overlay to anchor popup to map
const overlay = new ol.Overlay({
  element: container,
  autoPan: true,
  autoPanAnimation: {
    duration: 250,
  }
});

// add click handler to hide popup
closer.onclick = function () {
  overlay.setPosition(undefined);
  closer.blur();
  return false;
}

var style = new ol.style.Style({
  image: new ol.style.Icon({
    scale: 0.02,
    src: "data/media/new_wildfire_icon.png"
  })
});

// style object for polygons
var polygonStyle = new ol.style.Style({
  stroke: new ol.style.Stroke({
    color: "ff00ff",
    width: 1
  }),
  fill: new ol.style.Fill({
    color: "rgba(255, 255, 0, 0.5)"
  })
});

function makeDynamicGETRequest(map) {

  // base URL
  //var baseURL = "http://localhost:8080/raptor-backend-0.1-SNAPSHOT/vectors/states.geojson";
  var baseURL = "http://localhost:8080/vectors/states.geojson";

  // extents
  minx = map.getView().calculateExtent()[0];
  miny = map.getView().calculateExtent()[1];
  maxx = map.getView().calculateExtent()[2];
  maxy = map.getView().calculateExtent()[3];

  // generate url with extents parameters
  // we use ol.proj.toLonLat() to convert from pixel coordinates to longitude/latitude
  var url = baseURL + "?minx=" + ol.proj.toLonLat([minx, miny])[0] + "&miny=" + ol.proj.toLonLat([minx, miny])[1] + "&maxx=" + ol.proj.toLonLat([maxx, maxy])[0] + "&maxy=" + ol.proj.toLonLat([maxx, maxy])[1];

  // iterate through all layers in map
  // when we find our vector layer, set its url to updated url with extents parameters
  map.getLayers().forEach(function (layer) {
    if (layer instanceof ol.layer.Vector) {
      layer.getSource().setUrl(url);
      layer.getSource().refresh();
    }
  });
}

$(document).ready(function () {

  // create map
  var map = new ol.Map({
    target: "map",
    layers: [

      // OpenStreetMap
      new ol.layer.Tile({
        source: new ol.source.OSM()
      }),

      // multilevel visualization
      /*
      new ol.layer.Tile({
        source: new ol.source.XYZ({
          url: "data/multilevel/wildfire_visualization_4326_reversed/tile-{z}-{x}-{y}.png",
          tileSize: [256, 256],
          attributions: '<a href="https://davinci.cs.ucr.edu">&copy;DaVinci</a>'
        }),
        maxZoom: 12
      }),
      */

      // empty vector layer
      new ol.layer.Vector({
        //minZoom: 12,
        source: new ol.source.Vector({
          format: new ol.format.GeoJSON({featureProjection: "EPSG:3857"})
        }),
        style: function(feature) {
          return polygonStyle;
        }
      })
    ],
    overlays: [overlay],
    view: new ol.View({
      center: [-13694686.259677762, 4715193.587946976],
      zoom: 6
    })
  });

  //makeDynamicGETRequest(map);

  // add hover handler to render popup
  map.on("pointermove", function (evt) {
    if (evt.dragging) {
      return;
    }

    var p = evt.pixel;
    var feature = map.forEachFeatureAtPixel(p, function(feature) {
      return feature;
    });
    if (feature) {

      // if we're hovering over a feature, display feature information
      let popupContent = `
        County: ${feature.get("County")}
        <br>
        Acres: ${feature.get("Acres")}
        <br>
        Crop2014: ${feature.get("Crop2014")}
        <br>
        Date_Data_: ${feature.get("Date_Data_")}
      `;
      content.innerHTML = popupContent;

      // set pos of overlay at click coordinate
      const coordinate = evt.coordinate;
      overlay.setPosition(coordinate);

    } else {
      //overlay.setPosition(undefined);
      //closer.blur();
    }
  });

  // on singleclick, display current feature info at bottom of map
  map.on("singleclick", function (evt) {
    var p = evt.pixel;
    //console.log(evt.coordinate);
    var feature = map.forEachFeatureAtPixel(p, function(feature) {
      return feature;
    });
    if (feature) {
      // if we're clicking on a feature, display more info on the side
      document.getElementById("County").innerHTML = feature.get("County");
      document.getElementById("Acres").innerHTML = feature.get("Acres");
      document.getElementById("Crop2014").innerHTML = feature.get("Crop2014");
      document.getElementById("Date_Data").innerHTML = feature.get("Date_Data");
    }
  });

  // make dynamic GET request at end of map move event
  // only want to make request if zoom level is high enough
  map.on("moveend", function() {
    /*if (map.getView().getZoom() >= 12) {
      makeDynamicGETRequest(map);
    }*/
    makeDynamicGETRequest(map);
  });
});