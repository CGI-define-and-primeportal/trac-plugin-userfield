$(document).ready(function() {
  var $type = $("#type"),
      $wrapper = $("#user-groups"),
      $select = $("#select-user-groups"),
      $radios = $("input[name='all_or_selection']");

  $select.select2({width: 'resolve'});
  var $select2 = $("#s2id_select-user-groups");

  // Show the "Included Groups" row only when type "user" set
  $type.change(function() { $wrapper.toggle($type.val() == "user"); });
  $type.change();

  // If there's an initial set value of "all", hide the select2
  if($radios.filter(":checked").val() == "all") $select2.hide();

  // When we change the radio button's value, slide the select2 up/down
  $($radios).change(function() {
    if($(this).val() == "selection") {
      $select2.slideDown();
    }
    else {
      $select2.slideUp();
    }
  });
})
