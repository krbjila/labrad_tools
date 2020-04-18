(function () {

  var typeLookup = [];
  var colorLookup = {};
  var sequenceBoundaries = [];

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
      const maxpostime = sequence[TIMING_CHANNEL].slice(-1)[0][0] - x.domain()[0];
      const maxnegtime = -1 * x.domain()[0];

      if ($val*1e-3 > maxpostime) {
        $val = 1e3 * maxpostime;
      }
      else if ($val*1e-3 < maxnegtime) {
        $val = 1e3 * maxnegtime;
      }
      $(this).val($val.toFixed(3));
      updatePlot();
    }
  });

  $("#input-time-span").change(function () {
    $val = parseFloat($(this).val());
    if ($val === NaN || $val < 0) {
      alert("Please put a nonnegative number here!");
    }
    else {
      const maxtime = sequence[TIMING_CHANNEL].slice(-1)[0][0] - x.domain()[0];

      if ($val*1e-3 > maxtime) {
        $val = 1e3 * maxtime;
      }
      $(this).val($val.toFixed(3));
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
          sequence_array[i].scaledData = d.data.map(x => [x[0], x[1] / max]);
        });

        y = d3.scaleLinear()
          .domain([-1.1, 1.1])
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
          sequence_array[i].scaledData = sequence_array[i].data;
        });

        y = d3.scaleLinear()
          .domain([-11, 11])
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
            name: $(this).attr('data-name'),
            data: sequence[$idn],
            scaledData: sequence[$idn]
          }
        );
      });

      updateAxes();
      drawSequenceBoundaries();

      const path = svg.select("g.lines")
        .selectAll("path")
          .data(sequence_array)
          .join("path")
            .attr("fill", "none")
            .attr("clip-path", "url(#clip-rect)")
            .attr("stroke-width", 3)
            .attr("stroke", d => colorLookup[d.nameloc])
            .attr("d", d => line(d.scaledData));
      svg.call(mouseActions, path);
    }
  }

  function drawSequenceBoundaries() {
    sequenceBoundaries.length = 0;

    var time = 0;
    KRbVisualizer.sequences.forEach(function(d, i) {
      sequenceBoundaries.push({
        name: d.name,
        time: time
      });
      time += d.duration;
    });

    svg.select("g.sequence-lines")
      .selectAll("line")
        .data(sequenceBoundaries)
        .join("line")
          .attr("fill", "none")
          .attr("clip-path", "url(#clip-rect)")
          .attr("stroke-width", 1)
          .attr("stroke", "black")
          .attr("stroke-dasharray", "1, 3")
          .attr("stroke-linecap", "round")
          .attr("x1", d => x(d.time))
          .attr("x2", d => x(d.time))
          .attr("y1", d => margins.top)
          .attr("y2", d => height - margins.bottom);
  }

  function mouseActions(svg, path) {
    svg.on("mousemove", moved)
      .on("click", clicked)
      .on("mouseenter", entered)
      .on("mouseleave", left)

    const dot = svg.select("g.dot");
    const sequenceTag = svg.select("g.sequence-tag");
    const sequenceBackground = svg.select("g.sequence-background");


    function moved() {
      d3.event.preventDefault();
      const ym = y.invert(d3.event.layerY - margins.top);
      const xm = x.invert(d3.event.layerX - margins.left);

      if (xm >= x.domain()[1]) {
        return;
      }

      // First handle sequence borders
      const iseq1 = d3.bisectLeft(sequenceBoundaries.map(x => x.time), xm, 1);
      const iseq0 = iseq1 - 1;

      const time0 = Math.max(x.domain()[0], sequenceBoundaries[iseq0].time);
      var time1;
      if (iseq1 === sequenceBoundaries.length) {
        time1 = x.domain()[1];
      }
      else {
        time1 = Math.min(x.domain()[1], sequenceBoundaries[iseq1].time);
      }
      const anchor = 0.5 * (time0 + time1);

      sequenceTag
        .attr("transform", "translate(" + x(anchor) + "," + (height - margins.bottom) + ")")
        .select("text")
          .text(sequenceBoundaries[iseq0].name);

      sequenceBackground.select("rect")
        .attr("x", x(time0))
        .attr("width", x(time1) - x(time0));
      sequenceBackground.lower();

      // Next handle lines
      if (focusSet) {
        const channelData = sequence_array[focusIndex].scaledData;
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
        const i0s = sequence_array.map(d => d3.bisectLeft(d.scaledData.map(x => x[0]), xm, 1));
        const i1s = i0s.map(d => d - 1);

        // Again looks gnarly. Just want to find whether xm is closer to i0s[i] or i1s[i]
        // for each i
        const is = sequence_array.map(
          (d,i) => (d.scaledData[i0s[i]][0] - xm < xm - d.scaledData[i1s[i]][0]) ? i0s[i] : i1s[i]
        );
        const dys = sequence_array.map((d, i) => Math.abs(ym - d.scaledData[is[i]][1]));

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
      const val = sequence_array[focusIndex].scaledData[inner];

      dot.attr("transform", "translate("+ x(val[0]) + "," + y(val[1]) + ")")
        .raise();
      svg.select("#text-dot-name")
        .text(sequence_array[focusIndex].name);
      // Put the real voltage out
      svg.select("#text-dot-voltage")
        .text(sequence_array[focusIndex].data[inner][1].toFixed(3) + " V");

      path.attr("stroke", (d,i) => focusIndex === i ? colorLookup[d.nameloc] : "#ddd")
        .filter((d,i) => focusIndex === i).raise();
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
      sequenceTag.attr("display", null);
      sequenceBackground.attr("display", null);

      if (!focusSet) {
        path.attr("stroke", "#ddd");
      }
    }
    function left() {
      dot.attr("display", "none");
      sequenceTag.attr("display", "none");
      sequenceBackground.attr("display", "none");

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
      .attr("class", "lines");

    svg.append("g")
      .attr("class", "sequence-lines");

    svg.append("clipPath")
      .attr("id", "clip-rect")
      .append("rect")
        .attr("x", margins.left)
        .attr("y", margins.top)
        .attr("width", width - margins.left - margins.right)
        .attr("height", height - margins.top - margins.bottom);

    const dot = svg.append("g")
      .attr("class", "dot")
      .attr("display", "none")
    dot.append("circle")
      .attr("r", 2.5)
    dot.append("text")
      .attr("id", "text-dot-name")
      .attr("font-family", "sans-serif")
      .attr("font-size", 12)
      .attr("text-anchor", "middle")
      .attr("y", -10);
    dot.append("text")
      .attr("id", "text-dot-voltage")
      .attr("font-family", "sans-serif")
      .attr("font-size", 12)
      .attr("text-anchor", "middle")
      .attr("y", 15);

    svg.append("g")
      .attr("class", "sequence-tag")
      .attr("display", "none")
      .append("text")
        .attr("font-family", "sans-serif")
        .attr("font-size", 12)
        .attr("text-anchor", "middle")
        .attr("y", -10);

    svg.append("g")
      .attr("class", "sequence-background")
      .attr("display", "none")
      .append("rect")
        .attr("y", margins.top)
        .attr("height", height - margins.top - margins.bottom)
        .attr("fill", "#eee")
        .attr("stroke", "none");
  }

})();