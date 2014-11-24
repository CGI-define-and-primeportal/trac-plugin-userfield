/* ==================================
 * Userfield plugin v1.0 by Ian Clark
 * Copyright CGI 2013
 * =============================== */

$(document).ready(function($) {
  $(window.userfieldSelector).userField();
});


/**
 * Converts the original element into a select2 complete with users
 */
(function($) {

  var ALWAYSOPTIONS = {
    width: "off",
    formatResult: function(object, container, query) {
      if(object.hasOwnProperty("remote")) {
        container.addClass("remote").addClass("remote-" + object.remote);
        switch(object.remote) {
          case "closed":
            return "<i class='icon-plus-sign-alt'></i> " + object.text;
          case "loading":
            return "<i class='icon-spinner icon-spin'></i> " + object.text;
          case "open":
            return "<i class='icon-external-link-sign'></i> " + object.text;
        }
      }
      if(object.hasOwnProperty("none")) container.addClass("color-muted-dark");
      else if(object.hasOwnProperty("manual")) container.addClass("manual");
      else if(object.hasOwnProperty("current")) container.addClass("current");
      return object.text;
    }
  };

  $.fn.userField = function() {
    return this.each(function() {
      var $elem = $(this),
          groups = [], elmValue,

          // Process original input
          processed   = process($elem),
          $select     = processed[0],
          groups      = processed[1],
          elmValue    = processed[2],

          // Generate select2 options and data
          opts = generate_s2_options($select, groups, elmValue);

      // Replace original
      $select.insertAfter($elem);
      $elem.remove();

      // Construct select2
      $select.select2(opts).select2("val", elmValue);

      // Process clicking on remote group
      $select.on("select2-selecting", function(e) {
        event_option_selected(e, $select);
      });
    });
  };

  /**
   * Process the original element (input or select)
   * Return a hidden input to be used for the select2 object.
   * If the original was a select, disect the options for group references
   */
  function process($original) {
    var elmValue, groups = [];

    if($original.is("select")) {
      elmValue = $("option.current").val();
      $("option:not(.current)", $original).each(function() {
        groups.push($(this).val());
      });
    }
    else {
      elmValue = $original.val();
      groups = ["*"];
    }

    // Create our new hidden input to hold our select2 data
    var $select = $("<input type='hidden' />").attr({
      "id": $original.attr("id"),
      "class": $original.attr("class"),
      "name": $original.attr("name"),
      "value": elmValue
    });

    return [$select, groups, elmValue];
  }

  /**
   * Generate options to be used during the construct of the select2 object
   * Here we build our data tree, and add manual selection if permitted
   */
  function generate_s2_options($select, groups, elmValue) {
    var opts = $.extend({
      containerCssClass: $select.attr("class"),
      data: {
        more: false,
        results: []
      }
    }, ALWAYSOPTIONS);

    if(elmValue) {
      opts.data.results.push({
        id: elmValue, text: elmValue, current: true
      });
    }

    // Iterate over groups and construct tree
    var groupLength = groups.length;
    for(var i = 0; i < groupLength; i++) {
      var groupName = groups[i];
      // Wildcard for all groups
      if(groupName == "*") {
        for(var gName in window.userGroups) {
          opts.data.results.push(get_group_data(gName));
        }
        break;
      }
      else {
        if(groupName in window.userGroups) {
          opts.data.results.push(get_group_data(groupName));
        }
      }
    }

    // Allow for manual entry
    if($select.hasClass("manual") || !$select.hasClass("user-field")) {
      $.extend(opts, {
        createSearchChoice: function(term) {
          var groups = $select.data("select2").opts.data.results,
              groupCount = groups.length, i, found = false,
              lcTerm = term.toLowerCase();

          for(i = 0; i < groupCount; i ++) {
            var group = groups[i],
                children = group.children || [],
                childCount = children.length, j;

            for(j = 0; j < childCount; j ++) {
              var child = children[j];
              if(child.id && lcTerm == child.text.toLowerCase()) {
                found = true;
                break;
              }
            }
          }
          if(!found) {
            return {
              id: term,
              text: term,
              manual: true
            }
          }
        }
      });
    }

    return opts;
  }

  /**
   * Generate select2 style data optgroups and options
   * cache the results for reuse
   */
  var optgroupCache = {};
  function get_group_data(groupName) {
    var group = window.userGroups[groupName];
    if(group.members) {
      return data_optgroup(groupName, group);
    }
    else {
      return data_remote(groupName, group.label);
    }
  }

  function data_optgroup(name, data) {
    if(name in optgroupCache) return optgroupCache[name];
    var members = [],
        memberLength = data.members.length;

    for(var i = 0; i < memberLength; i ++) {
      var member = data.members[i];
      members.push({ 'id': member.id, 'text': (member.name || member.id) });
    }

    if(memberLength == 0) {
      members.push({ 'text': "No members found", 'none': true });
    }

    optgroup = {
      'text': data.label,
      'id': name,
      'children': members
    };
    optgroupCache[name] = optgroup;
    return optgroup;
  }

  function data_remote(name, label) {
    return {
      'id': name,
      'text': label,
      'remote': 'closed'
    }
  }

  /**
   * Retrieve remote group users using Ajax (cache again)
   */
  function get_results(object, $select, $dropdown) {
    if(object.id in optgroupCache) {
      data = optgroupCache[object.id];
      object.remote = "open";
      object.children = data.children;
      delete object.id;
      refresh($select, $dropdown);
    }
    else {
      $.ajax(window.tracBaseUrl + "ajax/groupsearch/acc", {
        type: "GET",
        data: { "group": object.id },
        dataType: "json",
        success: function(data, textStatus, jqXHR) {
          var members = data[0] ? data[0].members : [],
              memberCount = members.length, i = 0;

          object.remote = "open";
          object.children = [];

          for(i; i < memberCount; i ++) {
            var member = members[i];
            object.children.push({ 'id': member.id, 'text': (member.name || member.id) })
          }

          if(memberCount == 0) {
            object.children.push({ 'text': 'No members found', 'none': true });
          }

          optgroupCache[object.id] = object;
          delete object.id;

          refresh($select, $dropdown);
        }
      });
    }
  }

  /**
   * A nice little hack to allow a select2 to process new data
   * without disturbing the user experience 
   */
  function refresh($select, $dropdown) {
    if($dropdown.is(":visible")) {
      var scrollPos = $dropdown.scrollTop();
      $select.select2("close").select2("open");
      $dropdown.scrollTop(scrollPos);
    }
  }

  /**
   * Process selecting a remote group
   * Display loading message and call get_results
   */
  function event_option_selected(e, $select) {
    if(e.object.remote == "closed") {
      e.preventDefault();
      var s2Data = $select.data("select2"),
          $option = $(),
          $dropdown = $("ul.select2-results", s2Data.dropdown);

      e.object.remote = "loading";
      refresh($select, $dropdown);
      get_results(e.object, $select, $dropdown);
    }
  }

}(jQuery));