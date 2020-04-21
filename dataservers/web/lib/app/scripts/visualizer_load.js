var KRbVisualizer = {
  sequences: [],
  sequenceBoundaries: []
};

(function() {
  var experimentData;

  $.getJSON("./api/experiments")
    .done(function( data ) {
      experimentData = data;
      populateExperiments();
      processCookies();
  });

  $(".select-expt").change(function() {
    if (experimentData) {
      var $elts = $(".select-expt option:selected");
      var $target = $(".select-date");

      var expt = $elts.val();
      $target.empty();

      Object.keys(experimentData[expt])
        .sort()
        .reverse()
        .forEach(function(k, i) {
          var opt = new Option(k,k);
          opt.setAttribute("data-expt", expt);
          $target.append(opt);
        });
      $target.change()
    }
  });

  $(".select-date").change(function() {
    if (experimentData) {
      var $elts = $(".select-date option:selected");
      var $target = $(".select-version");

      var d = $elts.val();
      var expt = $elts.attr("data-expt");
      $target.empty();

      Object.keys(experimentData[expt][d])
        .sort(function(a,b) {
          return b-a;
        })
        .forEach(function(k, i) {
          var opt = new Option(k,k);
          opt.setAttribute("data-expt", expt);
          opt.setAttribute("data-date", d);
          $target.append(opt);
        });
      $target.change()
    }
  });

  $(".select-version").change(function() {
    if (experimentData) {
      var $elt = $(".select-version option:selected");

      var v = $elt.val()
      var d = $elt.attr("data-date");
      var expt = $elt.attr("data-expt");

      var s = d + "/" + expt + "#" + v;
      $(".header-sequence-list").text(s); 

      var params = {
        name: expt,
        date: d,
        version: v
      };
      setCookies(params);
      var qstr = $.param(params);

      $.getJSON("/krbtools/api/experiments/sequences?" + qstr)
        .done(function(data) {
          KRbVisualizer.sequences = data;
          populateSequences(data);

          $.getJSON("/krbtools/api/parameters")
            .done(function (pvs) {
              const pv_data = pvs.sequencer;
              populateSequenceJump(data, pv_data);
            });
        });
    }
  });

  function populateSequenceJump(data, pv_data) {
    $select = $(".select-jump");
    $select.empty();
    KRbVisualizer.sequenceBoundaries.length = 0;

    var ctime = 0;
    data.forEach(function(d,i) {
      var opt = new Option(d.name + " (" + ctime.toFixed(3) + " s)", ctime);
      var duration = d.duration;

      d.time_variables.forEach(function(k, i) {
        console.log(k);
        if (k in pv_data) {
          duration += pv_data[k];
        }
      });
      opt.setAttribute("data-time", ctime);
      opt.setAttribute("data-duration", d.duration);
      $select.append(opt);

      KRbVisualizer.sequenceBoundaries.push({
        name: d.name,
        time: ctime
      });

      ctime += d.duration;
    });
  }

  // Populate
  function populateExperiments() {
    Object.keys(experimentData)
      .sort(function(a,b) {
        return a.toLowerCase().localeCompare(b.toLowerCase());
      })
      .forEach(function(k,i) {
        $(".select-expt").append(
          new Option(k,k)
        );
      });
  };

  function setCookies(params) {
    Cookies.set("KRB_EXPERIMENT_NAME", params.name);
    Cookies.set("KRB_EXPERIMENT_DATE", params.date);
    Cookies.set("KRB_EXPERIMENT_VERSION", params.version);
  }

  function processCookies() {
    const cs = Cookies.get();

    if ("KRB_EXPERIMENT_NAME" in cs) {
      $(".select-expt option[value=" + cs["KRB_EXPERIMENT_NAME"] + "]").attr('selected', 'selected');
      $(".select-expt").change();

      if ("KRB_EXPERIMENT_DATE" in cs) {
        $(".select-date option[value=" + cs["KRB_EXPERIMENT_DATE"] + "]").attr('selected', 'selected');
        $(".select-date").change();

        if ("KRB_EXPERIMENT_VERSION" in cs) {
          $(".select-version option[value=" + cs["KRB_EXPERIMENT_VERSION"] + "]").attr('selected', 'selected');
          $(".select-version").change();
        }
      }
    }
  };

  // Populate
  function populateSequences(data) {
    const $t = $(".table-sequence");
    $t.empty();
    for (let i=0; i < data.length; i++) {
      var tr = $('<tr/>').appendTo($t);
      var th = $('<th/>')
        .attr('scope', "row")
        .text(i)
        .appendTo(tr);
      $('<td/>').text(data[i].name).appendTo(tr);
      $('<td/>').text(data[i].date).appendTo(tr);

      var duration = parseFloat(data[i].duration)*1000;
      var vars = data[i].time_variables;
      duration = Number(duration.toFixed(3))
      if (Number.isInteger(duration)) {
        duration = duration.toFixed(0);
      }
      else {
        duration = duration.toFixed(3);
      }
      for (let i=0; i < vars.length; i++) {
        duration += " + " + vars[i];
      }
      $('<td/>').text(duration).appendTo(tr);
      tr.appendTo($t);
    }
  };

})();