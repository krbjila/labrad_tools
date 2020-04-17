(function () {

  var typeLookup = [];
  var colorLookup = {};

  var sequence; var meta;
  var sequence_list;
  var sequence_array = [];
  var svg = d3.select("svg");
  var line, x, y, z, xAxis, yAxis;

  const digital_colors = [
    "#ff0000",
    "#ff7700",
    "#ffff00",
    "#00ff00",
    "#0000ff",
    "#8a2be2"
  ]
  const analog_colors = d3.schemeCategory10;
  console.log(analog_colors);

  var focusSet = false;
  var focusIndex;

  const width = 1000;
  const height = 300;
  const margins = {
    left: 30,
    right: 20,
    top: 20,
    bottom: 20
  };
  const TTL_HIGH = 5;

  const TIMING_CHANNEL = "Trigger@D15";

  generateLookup();
  getSequence();

  $(".check-channel").change(function() {
    updatePlot();
  });

  $(".check-scale").change(function() {
    updatePlot();
  });

  $(".select-jump").change(function() {
    updatePlot();
  });

  $("#input-time-start").change(function () {
    $val = parseFloat($(this).val());
    if ($val === NaN) {
      alert("Please put a number here!");
    }
    else {
      $(this).val($val);
      updatePlot();
    }
  });

  $("#input-time-span").change(function () {
    $val = parseFloat($(this).val());
    if ($val === NaN || $val < 0) {
      alert("Please put a nonnegative number here!");
    }
    else {
      $(this).val($val);
      updatePlot();
    }
  });

  function updateAxes() {
    if (sequence) {
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
            sequence_array[i].data = d.data.map(x => [x[0], (x[1] > 0) ? TTL_HIGH : 0]);
          }
        });

        y = d3.scaleLinear()
          .domain([-10, 10])
          .range([height - margins.top, margins.bottom]);
        yAxis = d3.axisLeft(y);

        svg.select("g.y.axis")
            .call(yAxis);
      }

      const $offset = parseFloat($(".select-jump").val());
      const $start = 1e-3 * parseFloat($("#input-time-start").val());
      const $span = 1e-3 * parseFloat($("#input-time-span").val());

      const xmin = Math.max($offset + $start, 0);
      const end = sequence[TIMING_CHANNEL].slice(-1)[0][0];
      const xmax = Math.min($offset+$start+$span, end);

      x = d3.scaleLinear()
        .domain([xmin, xmax])
        .range([margins.left, width - margins.right]);
      xAxis = d3.axisBottom(x);

      svg.select("g.x.axis")
        .call(xAxis);

    }
  }

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

      updateAxes();

      // // Trim data to domain
      // const xdom = x.domain();
      // const trimmedSequence = sequence_array
      //   .map(function (d,i) {
      //     const out = {
      //       nameloc: d.nameloc,
      //       data: d.data.slice(
      //         d3.bisectLeft(d.data.map(d => d[0]), xdom[0], 1),
      //         d3.bisectRight(d.data.map(d => d[0]), xdom[1], 1) + 1
      //         )
      //     };
      //     return out;
      //   });

      const clip = svg.append("clipPath")
        .attr("id", "clip-rect")
        .append("rect")
          .attr("x", margins.left)
          .attr("y", margins.top)
          .attr("width", width - margins.left - margins.right)
          .attr("height", height - margins.top - margins.bottom);

      const path = svg.select("g.lines")
        .selectAll("path")
          .data(sequence_array)
          .join("path")
            .attr("fill", "none")
            .attr("clip-path", "url(#clip-rect)")
            .attr("stroke-width", 2)
            .attr("stroke", d => colorLookup[d.nameloc])
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

    function moved() {
      d3.event.preventDefault();
      const ym = y.invert(d3.event.layerY - margins.top);
      const xm = x.invert(d3.event.layerX - margins.left);
      
      if (focusSet) {
        const channelData = sequence_array[focusIndex].data;
        const i0 = d3.bisectLeft(channelData.map(x => x[0]), xm, 1);
        const i1 = i0 - 1;
        var inner = channelData[i0][0] - xm < xm - channelData[i1][0] ? i0 : i1;
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

        focusIndex = 0;
        let temp = dys[0];
        for (let j=0; j < dys.length; j++) {
          if (dys[j] < temp) {
            temp = dys[j];
            focusIndex = j;
          }
        }
        var inner = is[focusIndex];
      }
      const val = sequence_array[focusIndex].data[inner];

      path.attr("stroke", (d,i) => focusIndex === i ? colorLookup[d.nameloc] : "#ddd")
        .filter((d,i) => focusIndex === i).raise();

      dot.attr("transform", "translate("+ x(val[0]) + "," + y(val[1]) + ")")
      dot.select("text")
        .text(sequence_array[focusIndex].nameloc + " = " + val[1].toFixed(3));
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

      if (!focusSet) {
        path.attr("stroke", "#ddd");
      }
    }
    function left() {
      dot.attr("display", "none");

      if (!focusSet){
        path.attr("stroke", d => colorLookup[d.nameloc]);
      }
    }
  }


  // Generate the list of channels
  function generateLookup() {
    var digital = 0;
    var analog = 0;
    var ad5791 = 0;

    $(".check-channel").each(function() {
      var $e = $(this);
      typeLookup[$e.attr("data-nameloc")] = $e.attr("data-type");

      if ($e.attr("data-type") === "digital") {
        colorLookup[$e.attr("data-nameloc")] = digital_colors[digital % digital_colors.length];
        digital++;
      }
      else if ($e.attr("data-type") === "analog") {
        colorLookup[$e.attr("data-nameloc")] = analog_colors[analog % analog_colors.length];
        analog++;
      }
      else {
        colorLookup[$e.attr("data-nameloc")] = analog_colors[ad5791 % analog_colors.length];
        ad5791++;
      }
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

})();