(function () {

  var typeLookup = [];
  var colorLookup = {};
  var sequenceBoundaries = [];

  var currentParameters = {};
  var previousParameters = {};
  var userParameters = {};

  var sequence; var meta;
  var sequence_list;
  var sequence_array = [];
  var svg = d3.select("svg");
  var line, x, y, yScaled, z, xAxis, yAxis;

  var xm, ym;

  var previousScale = 1;

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
  var mouseInFrame = false;

  const width = 1000;
  const height = 450;
  const margins = {
    left: 55,
    right: 20,
    top: 20,
    bottom: 40
  }
  const TTL_HIGH = 5;

  const TIMING_CHANNEL = "Trigger@D15";

  setupPlots();

  $(".check-channel").change(function() {
    updatePlot();
  });

  $(".check-scale").change(function() {
    updateX();
    updatePlot(true);
  });

  $(".select-jump").change(function() {
    updateX();
    updatePlot();
  });

  $(".select-version").change(function() {
    generateLookup();
    getSequence();
    getParameters();
    resetXControls();
    updateX();
    updatePlot(true);
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

      updateX();
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

      updateX();
      updatePlot();
    }
  });

  function resetXControls() {
    $(".select-jump option:selected").prop("selected", false);
    $(".select-jump option:first").prop("selected", "selected");

    $("#input-time-start").val(0);
    $("#input-time-span").val(2000);
  }

  function updateY() {
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
          .domain([-1.2, 1.2])
          .range([height - margins.bottom, margins.top]);

        svg.select("g.y.label")
          .select("text")
            .text("Scaled Voltage");
      }
      else {
        sequence_array.forEach(function(d,i) {
          if (typeLookup[d.nameloc] === "digital") {
            sequence_array[i].data = d.data.map(x => [x[0], (x[1] > 0) ? TTL_HIGH : 0]);
          }
          sequence_array[i].scaledData = sequence_array[i].data;
        });

        y = d3.scaleLinear()
          .domain([-12, 12])
          .range([height - margins.bottom, margins.top]);

        svg.select("g.y.label")
          .select("text")
            .text("Voltage");
      }
    }
  }

  function updateX() {
    if (sequence) {
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

  function updatePlot(flag = false) {
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

      updateY();

      if (flag) {
        yScaled = y;

        yAxis = d3.axisLeft(y);
        svg.select("g.y.axis")
          .call(yAxis);
      }

      drawSequenceBoundaries();

      const path = svg.select("g.lines")
        .selectAll("path")
          .data(sequence_array)
          .join("path")
            .attr("fill", "none")
            .attr("clip-path", "url(#clip-rect)")
            .attr("stroke-width", 3)
            .attr("d", d => line(d.scaledData));

      if (focusSet) {
        path.attr("stroke", (d, i) => i === focusIndex ? colorLookup[d.nameloc] : "#ddd")
          .filter((d,i) => i === focusIndex)
            .raise();
      }
      else {
        path.attr("stroke", d => colorLookup[d.nameloc]);
      }
      svg.call(mouseActions, path);
      svg.call(keyActions, path);

      svg.call(d3.zoom()
        .extent([[0,0], [width, height]])
        .scaleExtent([1,10])
        .on("zoom", zoomed));
    }
  }

  function zoomed() {
    const path = d3.select("g.lines").selectAll("path");

    yScaled = d3.event.transform.rescaleY(y).nice(); 
    yAxis = d3.axisLeft(yScaled);
    svg.select("g.y.axis")
      .call(yAxis);

    line = d3.line()
      .x(d => x(d[0]))
      .y(d => yScaled(d[1]));

    path.attr("d", d => line(d.scaledData));
  }

  function drawSequenceBoundaries() {
    sequenceBoundaries = KRbVisualizer.sequenceBoundaries;

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

  /* Tab through which channel has focus */
  function keyActions(svg, path) {
    d3.select("body").on("keydown", keyDown);

    const dot = svg.select("g.dot");

    function keyDown() {
      const key = d3.event.keyCode;
      // 9 is tab
      if (focusSet && mouseInFrame && sequence_array) {
        if (key === 9) {
          d3.event.preventDefault();
          const increment = d3.event.shiftKey ? -1 : 1;
          focusIndex = (focusIndex + increment) % sequence_array.length;
          if (focusIndex < 0) {
            focusIndex += sequence_array.length;
          }
          handleLinesFocus(xm, ym, dot, path)
        }
      }
    }
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

      const coords = d3.mouse(svg.node());

      ym = yScaled.invert(coords[1]);
      xm = x.invert(coords[0]);

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

      const bbox = sequenceTag.select("text").node().getBBox();
      sequenceTag
        .select("rect")
          .attr("x", bbox.x)
          .attr("y", bbox.y)
          .attr("width", bbox.width)
          .attr("height", bbox.height)
          .lower();

      sequenceBackground.select("rect")
        .attr("x", x(time0))
        .attr("width", x(time1) - x(time0));
      sequenceBackground.lower();

      if (sequence_array.length) {
        handleLinesFocus(xm, ym, dot, path);
      }
    }
    function clicked() {
      const coords = d3.mouse(svg.node());
      if (margins.top < coords[1]
          && coords[1] < height - margins.bottom 
          && margins.left < coords[0]
          && coords[0] < width - margins.right)
        focusSet = !focusSet;
    }
    function entered() {
      dot.attr("display", null);
      sequenceTag.attr("display", null);
      sequenceBackground.attr("display", null);

      mouseInFrame = true;

      if (!focusSet) {
        path.attr("stroke", "#ddd");
      }
    }
    function left() {
      dot.attr("display", "none");
      sequenceTag.attr("display", "none");
      sequenceBackground.attr("display", "none");

      mouseInFrame = false;

      if (!focusSet){
        path.attr("stroke", d => colorLookup[d.nameloc]);
      }
    }
  }


  function handleLinesFocus(xm, ym, dot, path) {
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

    dot.attr("transform", "translate("+ x(val[0]) + "," + yScaled(val[1]) + ")")
      .raise();
    svg.select("#text-dot-name")
      .text(sequence_array[focusIndex].name);

    // Put the real voltage out
    svg.select("#text-dot-voltage")
      .text(sequence_array[focusIndex].data[inner][1].toFixed(3) + " V");

    path.attr("stroke", (d,i) => focusIndex === i ? colorLookup[d.nameloc] : "#ddd")
      .filter((d,i) => focusIndex === i).raise();
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

    $.getJSON("./api/experiments?" + qstr)
      .done(function(data) {
        previousParameters = data.data.sequencer;

        // data.data.sequencer has values that are lists
        // For simplicity we'll take the first value in each list
        // Also the post request gets messed up if they are lists
        // because the keys in the dict become e.g. "*RbDet[]"
        // instead of "*RbDet"
        Object.keys(previousParameters)
          .forEach(function(k, i) {
            previousParameters[k] = previousParameters[k][0];
          });

        setupAutocomplete();

        $.post("./api/experiments/plottable?" + qstr, previousParameters)
          .done(function(data) {
            var s = JSON.parse(data);
            sequence = s.plottable;
            meta = s.meta;
          });
      });
  }

  function getParameters() {
    $.getJSON("./api/parameters")
      .done(function(data) {
        currentParameters = data.sequencer;
      });
  }

  function setupAutocomplete() {
    const p = Object.keys(previousParameters);
    const $input = $("#input-parameters");
    $input.autocomplete({
      source: p
    });
    $input.autocomplete("option", "appendTo", ".parameter-list");
  }

  $("#input-parameters").change(function(){
    const $val = $(this).val();
    const $ul = $(".ul-parameters");

    if ($val in previousParameters) {
      if (!($val in userParameters)) {
        var $li = $("<li />")
          .attr("class", "list-group-item li-parameters")
          .attr("id", "li-parameters-" + $val.slice(1,-1))
          .attr("data-parameter", $val)
          .appendTo($ul);
        var $row = $("<div />")
          .attr("class", "row")
          .appendTo($li);
        var $col0 = $("<div />")
          .attr("class", "col-sm-1")
          .appendTo($row);
        var $col1 = $("<div />")
          .attr("class", "col-sm-3")
          .appendTo($row);
        var $col2 = $("<div />")
          .attr("class", "col-sm-3")
          .appendTo($row);
        var $col3 = $("<div />")
          .attr("class", "col-sm-2")
          .appendTo($row);
        var $col4 = $("<div />")
          .attr("class", "col-sm-2")
          .appendTo($row);

        var $btn = $("<button />")
          .attr("type", "button")
          .attr("class", "close btn-parameter-remove")
          .attr("id", "btn-parameter-remove-" + $val.slice(1,-1))
          .attr("aria-label", "Close")
          .attr("data-parameter", $val)
          .appendTo($col0);

        $("<span />")
          .attr("aria-hidden", "true")
          .html("&times;")
          .appendTo($btn);

        $("<button />")
          .attr("type", "button")
          .attr("class", "btn btn-outline-secondary btn-parameter-set-current")
          .attr("id", "btn-parameter-set-current-" + $val.slice(1,-1))
          .attr("data-parameter", $val)
          .text("Current")
          .appendTo($col4);

        $("<button />")
          .attr("type", "button")
          .attr("class", "btn btn-outline-primary btn-parameter-reset")
          .attr("id", "btn-parameter-reset-" + $val.slice(1,-1))
          .attr("data-parameter", $val)
          .text("Default")
          .appendTo($col3);

        $("<input />")
          .text($val)
          .attr("class", "form-control input-change-parameters")
          .attr("id", "input-change-parameters-" + $val.slice(1,-1))
          .attr("data-parameter", $val)
          .attr("type", "text")
          .val(previousParameters[$val])
          .appendTo($col2);
        $("<label />")
          .text($val)
          .attr("for", "#input-change-parameters-" + $val.slice(1,-1))
          .appendTo($col1);

        userParameters[$val] = previousParameters[$val];

        $("#input-change-parameters-" + $val.slice(1,-1)).change(function () {
          const $v = parseFloat($(this).val());
          const $p = $(this).attr("data-parameter");
          if ($v) {
            userParameters[$p] = $v;
          }
        });
        $("#btn-parameter-remove-" + $val.slice(1,-1)).click(function () {
          const $p = $(this).attr("data-parameter");
          delete userParameters[$p];
          $("#li-parameters-" + $p.slice(1,-1)).remove();
        });
        $("#btn-parameter-set-current-" + $val.slice(1,-1)).click(function() {
          const $p = $(this).attr("data-parameter");

          if ($p in currentParameters) {
            userParameters[$p] = currentParameters[$p];
            $("#input-change-parameters-" + $val.slice(1,-1)).val(parseFloat(currentParameters[$p]));
          }
        });
        $("#btn-parameter-reset-" + $val.slice(1,-1)).click(function() {
          const $p = $(this).attr("data-parameter");

          if ($p in previousParameters) {
            userParameters[$p] = previousParameters[$p];
            $("#input-change-parameters-" + $val.slice(1,-1)).val(parseFloat(previousParameters[$p]));
          }
        });
      }
    }
  });

  $(".btn-set-parameters").click(function() {
    const session = {
      name: Cookies.get("KRB_EXPERIMENT_NAME"),
      date: Cookies.get("KRB_EXPERIMENT_DATE"),
      version: Cookies.get("KRB_EXPERIMENT_VERSION")
    }; 
    var qstr = $.param(session);
    $.post("./api/experiments/plottable?" + qstr, userParameters)
      .done(function(data) {
        var s = JSON.parse(data);
        sequence = s.plottable;
        updatePlot(true);
      });
  });

  $(".btn-reset-parameters").click(function() {
    console.log("hi");
  });

  function setupPlots() {
    svg.attr('width', width)
      .attr('height', height);

    x = d3.scaleLinear()
      .domain([0, 2])
      .range([margins.left, width - margins.right]);
    xAxis = d3.axisBottom(x);

    y = d3.scaleLinear()
      .domain([-12, 12]).nice()
      .range([height - margins.bottom, margins.top]);
    yAxis = d3.axisLeft(y);

    yScaled = y;

    line = d3.line()
    	.x(d => x(d[0]))
    	.y(d => yScaled(d[1]));

    svg.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + (height - margins.bottom) + ")")
      .call(xAxis);

    svg.append("g")
      .attr("class", "x label")
      .attr("transform", "translate(" + ((width + margins.left - margins.right)/2) + "," + (height - margins.bottom) + ")")
      .append("text")
        .attr("text-anchor", "middle")
        .attr("font-family", "sans-serif")
        .attr("font-size", 16)
        .attr("y", 35)
        .text("Time (s)");

    svg.append("g")
      .attr("class", "y axis")
      .attr("transform", "translate(" + margins.left + ",0)")
      .call(yAxis);

    svg.append("g")
      .attr("class", "y label")
      .attr("transform", "translate(0," + ((height + margins.top - margins.bottom)/2) + ")")
      .append("text")
        .attr("text-anchor", "middle")
        .attr("font-family", "sans-serif")
        .attr("font-size", 16)
        .attr("y",20)
        .attr("transform", "rotate(-90)")
        .text("Voltage");

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

    const tag = svg.append("g")
      .attr("class", "sequence-tag")
      .attr("display", "none");
    tag.append("rect")
        .attr("fill", "#eee")
        .attr("stroke", "none");
    tag.append("text")
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