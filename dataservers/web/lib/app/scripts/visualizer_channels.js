var checkState = {
  last: -1,
  shiftPressed: false,
  lookupList: []
};

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
$(".btn-channel-enable").click(function() {
  const dev = $(this).attr("data-device");
  $(".check-channel-"+dev).prop("checked", true);
});

// Disables all channels in a device
$(".btn-channel-disable").click(function() {
  const dev = $(this).attr("data-device");
  $(".check-channel-"+dev).prop("checked", false);
});

// Disables all channels
$(".btn-channel-all-off").click(function() {
  $(".check-channel").prop("checked", false);
});

// Disables all channels
$(".btn-channel-all-on").click(function() {
  $(".check-channel").prop("checked", true);
});

// Generate the list of channels
function generateLookup() {
  $(".check-channel").each(function() {
    checkState.lookupList.push($(this).attr("id"));
  });
}