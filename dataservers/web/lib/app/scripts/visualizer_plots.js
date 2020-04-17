var typeLookup = [];
var sequence; var meta;
var sequence_array = [];
var svg = d3.select("svg");
var line, x, y, z, xAxis, yAxis;

var focusSet = false;

const width = 1000;
const height = 300;
const margins = {
  left: 30,
  right: 20,
  top: 20,
  bottom: 20
};
const TTL_HIGH = 5;

generateLookup();
getSequence();

$(".check-channel").change(function() {
  updatePlot();
});

$(".check-scale").change(function() {
  updatePlot();
});

function updatePlot() {
  if (sequence) {
    // Empty array
    sequence_array.length = 0;
    // Loop through checkboxes
    $(".check-channel:checked").each(function() {
      var $idn = $(this).attr('data-nameloc');
      sequence_array.push(
        {
          nameloc: $idn,
          data: sequence[$idn]
        }
      );
    });

    if ($(".check-scale").is(":checked")) {
      sequence_array.forEach(function(d,i) {
        // Remember that each step in d.data is [time, value]
        let max = Math.max(-1.0*d3.min(d.data, x => x[1]), d3.max(d.data, x => x[1]));
        // Avoid divide by zero
        max = Math.max(1, max);
        sequence_array[i].data = d.data.map(x => [x[0], x[1] / max]);
      });

      y = d3.scaleLinear()
        .domain([-1, 1])
        .range([height - margins.top, margins.bottom]);
      yAxis = d3.axisLeft(y);

      svg.select("g.y.axis")
          .call(yAxis);
    }
    else {
      sequence_array.forEach(function(d,i) {
        if (typeLookup[d.nameloc] === "digital") {
          sequence_array[i].data = d.data.map(x => [x[0], TTL_HIGH*x[1] ]);
        }
      });

      y = d3.scaleLinear()
        .domain([-10, 10])
        .range([height - margins.top, margins.bottom]);
      yAxis = d3.axisLeft(y);

      svg.select("g.y.axis")
          .call(yAxis);
    }

    z = d3.scaleOrdinal(d3.schemeCategory10)
      .domain(Array.from(Array(10).keys()));

    const path = svg.select("g.lines")
      .selectAll("path")
        .data(sequence_array)
          .join("path")
          .attr("fill", "none")
          .attr("stroke-width", 2)
          .attr("stroke", (d,i) => z(i % 10))
          .attr("d", d => line(d.data));
    
    svg.call(mouseActions, path);
  }
}

function mouseActions(svg, path) {
  svg.on("mousemove", moved)
    .on("click", clicked)
    .on("mouseenter", entered)
    .on("mouseleave", left)

  const dot = svg.append("g")
    .attr("display", "none");
  dot.append("circle")
    .attr("r", 2.5);
  dot.append("text")
      .attr("font-family", "sans-serif")
      .attr("font-size", 10)
      .attr("text-anchor", "middle")
      .attr("y", -10);

  var outer, inner;

  function moved() {
    d3.event.preventDefault();
    const ym = y.invert(d3.event.layerY - margins.top);
    const xm = x.invert(d3.event.layerX - margins.left);
    
    if (focusSet) {
      const channelData = sequence_array[outer].data;
      const i0 = d3.bisectLeft(channelData.map(x => x[0]), xm, 1);
      const i1 = i0 - 1;
      inner = channelData[i0][0] - xm < xm - channelData[i1][0] ? i0 : i1;
    }
    else {
          // Yikes! This looks gnarly but is not so bad
      // We need to get the closest x-axis data value to our mouse
      // If we have an ordered array ts = [t0, t1, t2, ...], bisectLeft(ts, t)
      // returns the index where we can insert t
      // However need to do several maps over this to get into the correct arrays
      const i0s = sequence_array.map(d => d3.bisectLeft(d.data.map(x => x[0]), xm, 1));
      const i1s = i0s.map(d => d - 1);

      // Again looks gnarly. Just want to find whether xm is closer to i0s[i] or i1s[i]
      // for each i
      const is = sequence_array.map(
        (d,i) => (d.data[i0s[i]][0] - xm < xm - d.data[i1s[i]][0]) ? i0s[i] : i1s[i]
      );
      const dys = sequence_array.map((d, i) => Math.abs(ym - d.data[is[i]][1]));

      outer = 0;
      let temp = dys[0];
      for (let j=0; j < dys.length; j++) {
        if (dys[j] < temp) {
          temp = dys[j];
          outer = j;
        }
      }
      inner = is[outer];
    }
    const val = sequence_array[outer].data[inner];

    path.attr("stroke", (d,i) => outer === i ? z(i % 10) : "#ddd")
      .filter((d,i) => outer === i).raise();

    dot.attr("transform", "translate("+ x(val[0]) + "," + y(val[1]) + ")")
    dot.select("text")
      .text(sequence_array[outer].nameloc + " = " + val[1].toPrecision(3));
  }
  function clicked() {
    if (margins.top < d3.event.layerY
        && d3.event.layerY < height - margins.bottom 
        && margins.left < d3.event.layerX
        && d3.event.layerX < width - margins.right)
      focusSet = !focusSet;
  }
  function entered() {
    dot.attr("display", null);  

    if (!focusSet) 
      path.attr("stroke", "#ddd");
  }
  function left() {
    dot.attr("display", "none");

    if (!focusSet)
      path.attr("stroke", (d, i) => z(i % 10));
  }
}


// Generate the list of channels
function generateLookup() {
  $(".check-channel").each(function() {
    typeLookup[$(this).attr("data-nameloc")] = $(this).attr("data-type");
  });
}

function getSequence() {
  const session = {
    name: Cookies.get("KRB_EXPERIMENT_NAME"),
    date: Cookies.get("KRB_EXPERIMENT_DATE"),
    version: Cookies.get("KRB_EXPERIMENT_VERSION")
  }; 
  var qstr = $.param(session);
  $.getJSON("./api/experiments/plottable?" + qstr)
    .done(function(data) {
      sequence = data.plottable;
      meta = data.meta;

      setupPlots();
    });
}

function setupPlots() {
  svg.attr('width', width)
    .attr('height', height);

  x = d3.scaleLinear()
    .domain([0, 40])
    .range([margins.left, width - margins.right]);
  xAxis = d3.axisBottom(x);

  y = d3.scaleLinear()
    .domain([-5, 5])
    .range([height - margins.top, margins.bottom]);
  yAxis = d3.axisLeft(y);

  line = d3.line()
  	.x(d => x(d[0]))
  	.y(d => y(d[1]));

  svg.attr("transform", "translate(" + margins.left + "," + margins.top + ")");

  svg.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + (height - margins.bottom) + ")")
    .call(xAxis);

  svg.append("g")
    .attr("class", "y axis")
    .attr("transform", "translate(" + margins.left + ",0)")
    .call(yAxis);

  svg.append("g")
    .attr("class", "lines")
}