var sel2options = {
  formatResult: function(item) {
    var $elm = $(item.element);
    if($elm.hasClass("remote")) {
      if($elm.hasClass("users-loading")) {
        return "<i class='icon-spinner icon-spin'></i> " + item.text;
      }
      else {
        return "<i class='icon-plus-sign-alt'></i> " + item.text;
      }
    }
    else if($elm.hasClass("remote-open")) {
      return "<i class='icon-external-link-sign'></i> " + item.text;
    }
    else {
      return item.text;
    }
  },
};

// Cache each group in case we need to use it more than once
var optgroups = {};

// Create an optgroup given a name and data
function create_optgroup(name, data) {
  var groupMembers = data.members;
  if(!optgroups[name]) {
    var $optgroup = $("<optgroup label='" + data.label + "'></optgroup>"),
        memberCount = groupMembers.length;
    for(var i = 0; i < memberCount; i ++) {
      var member = groupMembers[i];
      $optgroup.append("<option value='" + member.username + "'>" +
                         (member.name || member.username) +
                       "</option>");
    }
    optgroups[name] = $optgroup;
  }
  return optgroups[name].clone();
}
function create_remote_option(name, label) {
  return $("<option class='remote' value='" + name + "'>" + label + "</option>");
}

$(document).ready(function($) {

  $(userfield_selector).each(function() {
    var $select = $(this);
    var $options = $("option:not(.current)", this);
    $.each($options, function() {
      var groupName = $(this).val();
      var group = window.userGroups[groupName];
      // Group is valid
      if(group) {
        // Group has members, convert to optgroup
        if(group.members) {
          $(this).replaceWith(create_optgroup(groupName, group));
        }
        // Group has no members, mark as remote
        else {
          $(this).replaceWith(create_remote_option(groupName, group.label));
        }
      }

      // Wildcard to select all groups
      else if(groupName == "*") {
        $(this).remove();
        for(groupName in window.userGroups) {
          var group = window.userGroups[groupName];
          if(group.members) {
            $select.append(create_optgroup(groupName, group));
          }
          else {
            $select.append(create_remote_option(groupName, group.label));
          }
        }
        return false;
      }
    });

    $(this).select2(sel2options);
    $(this).on("select2-selecting", function(e) {
      if($(e.object.element).hasClass("remote")) {
        $(e.object.element).addClass("users-loading");

        var $option = $(e.object.element),
            $optionsInSelect = $("option", this),
            indexOfOption = $optionsInSelect.index($option);

        this.selectedIndex = indexOfOption

        $(this).select2(sel2options);
        $(this).select2("open");
        e.preventDefault();
        get_results(this, e.val, $option, indexOfOption);
      }
    });
  });

});

function get_results(select, group, $option, selectedIndex) {
  $.ajax(window.tracBaseUrl + "ajax/groupsearch/acc", {
    type: "GET",
    data: { "group": group },
    dataType: "json",
    success: function(data, textStatus, jqXHR) {
      $expanded = format_results($option.text(), data);
        $option.after($expanded).remove();
        select.selectedIndex = selectedIndex;

        $(select).select2(sel2options);
        $(select).select2("open");
    }
  });
}

function format_results(label, results) {
  var $optgroup = $("<optgroup class='remote-open' label='" + label + "'></optgroup>");
  if(results.length == 1) {
    var groupMembers = results[0].children,
        memberCount = groupMembers.length;

    for(var j = 0; j < memberCount; j ++) {
      $optgroup.append("<option value='" + groupMembers[j].id + "'>" +
                         groupMembers[j].displayName + 
                       "</option>");
    }
  }
  return $optgroup;
}