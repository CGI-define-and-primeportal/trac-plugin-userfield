$(document).ready(function() {
  var $type = $("#type"),
      $wrapper = $("#user-groups"),
      $select = $("#select-user-groups"),
      $radios = $("input[name='all_or_selection']");

  $select.select2({width: 'resolve', placeholder: 'Select groups'});
  var $select2 = $("#s2id_select-user-groups");

  // Show the "Included Groups" row only when type "user" set
  $type.change(function() { $wrapper.toggle($type.val() == "user"); });
  $type.change();

  // If there's an initial set value of "all", hide the select2
  if($radios.filter(":checked").val() == "all") $select2.hide();

  // When we change the radio button's value, show the select2
  $($radios).change(function() {
    if($(this).val() == "selection") {
      $select2.show();
    }
    else {
      $select2.hide();
    }
  });
})
