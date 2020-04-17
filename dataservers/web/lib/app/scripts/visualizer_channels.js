(function() {

  var checkState = {
    last: -1,
    shiftPressed: false,
    lookupList: []
  };

  var toggleState = true;
  var deviceToggleState = {};

  populateToggleStates();
  generateLookup();

  // Implement shift-click
  $(".check-channel").click(function() {
    const id = $(this).attr('id');
    var index = checkState.lookupList
                  .findIndex(element => element === id);

    if (checkState.last >= 0 && checkState.shiftPressed) {
      var poll = 0;
      const i0 = Math.min(index, checkState.last);
      const i1 = Math.max(index, checkState.last);
      const idlist = checkState.lookupList.slice(i0, i1);

      idlist.forEach(function(k,i) {
          poll += ($("#"+k).is(":checked")) ? 1 : -1;
        });
      const state = (poll > 0) ? false : true;
      idlist.forEach(function(k,i) {
        $("#"+k).prop("checked", state);
      });
    }
    checkState.last = index;
  });

  // Watch for shift, for shift-clicking
  $(document).keydown(function(event) {
    if (event.which == 16) {
      checkState.shiftPressed = true;
    }
  })
  .keyup(function(event) {
    if (event.which == 16) {
      checkState.shiftPressed = false;
    }
  });

  // Enables all channels in a device
  $(".btn-device-toggle").click(function() {
    const dev = $(this).attr("data-device");
    const $btn = $(this);
    if (toggleState) {
      $(".check-channel-" + dev).prop("checked", true);
      $btn.text("All off");
      $btn.removeClass("btn-dark");
      $btn.addClass("btn-success");
      toggleState = false;
    }
    else {
      $(".check-channel-" + dev).prop("checked", false);
      $btn.text("All on");
      $btn.removeClass("btn-success");
      $btn.addClass("btn-dark");
      toggleState = true;
    }
     $(".check-channel").each(function(i, elt) {
      if (i === 0) {
        $(this).change();
      }
    });
  });

  // Enables/Disables all channels
  $(".btn-all-toggle").click(function() {
    const $btn = $(this);
    if (toggleState) {
      $(".check-channel").prop("checked", true);
      $btn.text("Turn all channels off");
      $btn.removeClass("btn-dark");
      $btn.addClass("btn-success");
      toggleState = false;
    }
    else {
      $(".check-channel").prop("checked", false);
      $btn.text("Turn all channels on");
      $btn.removeClass("btn-success");
      $btn.addClass("btn-dark");
      toggleState = true;
    }
    $(".check-channel").each(function(i, elt) {
      if (i === 0) {
        $(this).change();
      }
    });
  });

  function populateToggleStates() {
    $("btn-device-toggle").each(function(i, elt) {
      deviceToggleState[$(this).attr("data-device")] = false;
    });
  }

  // Generate the list of channels
  function generateLookup() {
    $(".check-channel").each(function() {
      checkState.lookupList.push($(this).attr("id"));
    });
  }

})();