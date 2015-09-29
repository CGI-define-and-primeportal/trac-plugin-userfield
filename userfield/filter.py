from trac.core import *
from trac.perm import PermissionSystem
from trac.web.api import IRequestFilter, ITemplateStreamFilter
from trac.web.chrome import (ITemplateProvider, add_script, add_script_data)
from trac.ticket.api import ITicketManipulator
from trac.ticket.web_ui import TicketModule
from trac.config import BoolOption

from trac.web.session import DetachedSession

from genshi.builder import tag
from genshi.filters.transform import Transformer

from autocompleteplugin.model import AutoCompleteGroup

from simplifiedpermissionsadminplugin.model import Group
from simplifiedpermissionsadminplugin.api import SimplifiedPermissionsSystem

from traceback import format_exc
import re

from api import IUserFieldUser

class UserFieldModule(Component):
    """A module providing a user custom field based on user group."""

    transform_owner_reporter = BoolOption('userfield', 'transform_owner_reporter', default='true',
        doc='Transform the owner, reporter fields into user fields too')

    implements(ITicketManipulator, ITemplateStreamFilter)

    extra_templates = ExtensionPoint(IUserFieldUser)

    # ITemplateStreamFilter methods
    def filter_stream(self, req, method, filename, stream, data):
        selector = ['.user-field']
        page_map = {
            "ticket.html": ["#field-owner", "#field-reporter"],
            "query.html": ["#mods-filters input[name$='_" + field + "']"
                            for field in ("owner", "reporter")],
            "admin_components.html": ["input[name='owner']"],
            "taskboard.html": ["input[class='user-field']"]
        }

        page_map["hours_timeline.html"] = page_map["query.html"]

        def _template_filenames():
            for plugin in self.extra_templates:
                for filename in plugin.get_templates():
                    yield filename

        if filename in page_map:
            if filename == "ticket.html":
                selector.extend('#field-' + n for n in self._user_fields())
            if self.transform_owner_reporter:
                selector.extend(page_map[filename])

        if filename in page_map or filename in _template_filenames():
            self._add_groups_data(req)
            add_script_data(req, {'userfieldSelector': ','.join(selector) })
            add_script(req, 'userfield/js/userfield.js')

        return stream

    # ITicketManipulator methods
    def prepare_ticket(self, req, ticket, fields, actions):
        pass

    def validate_ticket(self, req, ticket):
        """Validate any user fields by checking to see if the specified user
        belongs to any of the fields' allowed groups"""
        for field in self._user_fields():
            flc = TicketModule(self.env).field_layout_controller
            fl_config = flc.get_layout_for_field_on_type(ticket['type'],field)
            manual_entry = self.config.get("ticket-custom", field + ".manual")

            if not manual_entry and fl_config:
                username = (ticket[field] or u'').strip()
                valid_groups = self._get_valid_groups(field)
                valid = False

                if not username and not fl_config.get("mandatory"):
                    continue

                try:
                    spsystem = SimplifiedPermissionsSystem(self.env)
                    for provider in spsystem.user_lookup_providers:
                        info = provider.fetch_user_data(username)
                        if info and "groups" in info:
                            if any(g in info["groups"] for g in valid_groups):
                                valid = True
                                break

                    if valid:
                        continue
                    else:
                        yield field, ("User '%s', selected for field '%s' does"
                                      " not appear to be a member of any of"
                                      " the valid groups '%s'" % (username,
                                        field, ", ".join(valid_groups)))

                except Exception:
                    self.log.warn('UserFieldModule: Got an exception, '
                                  'assuming it is a validation failure.\n%s',
                                  format_exc())
                    yield field, ("Field %s does not appear to contain a valid"
                                  " user" % (field))

    def _add_groups_data(self, req, allow_manual=False):
        perms = sorted(PermissionSystem(self.env).get_all_permissions())
        autocomplete = AutoCompleteGroup(self.env)

        all_groups = set(Group.groupsBy(self.env))
        # TODO: we should remove the autocomplete plugin, at least
        # once userfield can handle "cc style" fields (e.g., multiple
        # users selected) and then I think userfieldplugin should take over ownership
        # of the "shown_groups" settings
        shown_groups = autocomplete.get_autocomplete_values('shown_groups')

        groups = {}
        for group_name in shown_groups:
            group = Group(self.env, group_name)
            groups[group_name] = { 'label': group.label }
            if not group.external_group:
                groups[group_name]['members'] = []
                for subject, permission in perms:
                    if permission == group_name and subject not in all_groups:
                        subject_data = {'id': subject}
                        session = DetachedSession(self.env, subject)
                        if 'name' in session:
                            subject_data['name'] = session['name']
                        groups[group_name]['members'].append(subject_data)

        add_script_data(req, {'userGroups': groups })

    # Internal methods
    def _user_fields(self):
        # XXX: Will this work when there is no ticket-custom section? <NPK>
        for key, value in self.config['ticket-custom'].options():
            if len(key.split(".")) == 1 and value == "user":
                yield key.split('.', 1)[0]

    def _get_valid_groups(self, field):
        allowed_groups = self.config.get("ticket-custom", field+".groups")
        if not allowed_groups:
            return []
        elif allowed_groups == "*":
            return [sid for sid in Group.groupsBy(self.env)]
        else:
            return allowed_groups.split("|")


class CustomFieldAdminTweak(Component):
    implements(ITemplateStreamFilter, IRequestFilter, ITemplateProvider)

    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('userfield', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []

    def pre_process_request(self, req, handler):
        valid_page = req.path_info.startswith(u"/admin/ticket/customfields")
        if req.method == "POST" and valid_page:
            if req.args.get('type') == 'user':
                self.config.set('ticket-custom', '%s.manual'%(req.args.get('name')),
                                req.args.get("manual_selection") == "manual" and "true" or "false")

                if req.args.get("all_or_selection") == "all":
                    self.config.set('ticket-custom',
                                    '%s.groups'%(req.args.get('name')), '*')
                else :
                    user_groups = req.args.get("user_groups", [])
                    if isinstance(user_groups, list):
                        user_groups = "|".join(user_groups)

                    self.config.set('ticket-custom',
                                    '%s.groups'% (req.args.get('name')),
                                    user_groups)
        return handler

    def post_process_request(self, template, content_type):
        return (template, content_type)

    def filter_stream(self, req, method, filename, stream, data):

        select = tag.select(
                     id="select-user-groups",
                     multiple="multiple",
                     name="user_groups",
                 )

        edit_name = req.path_info.replace("/admin/ticket/customfields", "")[1:]
        valid_edit = re.search('^[a-zA-Z][a-zA-Z0-9_]+$', edit_name)

        currently_editing = edit_name and valid_edit

        if currently_editing:
            groups = self.config.get("ticket-custom", edit_name+".groups")
            groups = groups.split("|")
        else:
            groups = []

        is_manual = self.config.getbool("ticket-custom", edit_name+".manual")

        manual = tag.div(
                    tag.label(
                        "Allow typing a name which is not in the list:",
                        for_="manual_selection",
                        class_="fixed-width-label"
                    ),
                    tag.input(
                        value="manual",
                        checked="checked" if is_manual else None,
                        type_="checkbox",
                        name="manual_selection"
                    ),
                    class_="field"
                )

        radios = tag(
                    tag.label(
                        "All ",
                        tag.input(
                            type="radio",
                            value="all",
                            name="all_or_selection",
                            checked=("checked" if "*" in groups else None),
                        )
                    ),
                    tag.span(
                        " or ",
                        class_="color-muted"
                    ),
                    tag.label(
                        "Selection ",
                        tag.input(
                            type="radio",
                            value="selection",
                            name="all_or_selection",
                            checked=(None if "*" in groups else "checked"),
                        ),
                        style="padding-right: 5px"
                    ))

        autocomplete = AutoCompleteGroup(self.env)
        for sid in autocomplete.get_autocomplete_values('shown_groups'):
            select.append(tag.option(
                             Group(self.env, sid).label, 
                             value=sid,
                             selected=("selected"
                                       if sid in groups or "*" in groups
                                       else None)
                         ))

        if filename == "customfieldadmin.html":
            add_script(req, 'userfield/js/customfield-admin.js')
            selected = None 
            customfield = data['cfadmin'].get('customfield', None)
            if customfield:
                if customfield['type'] == 'user':
                    selected = 'selected' 
            stream = stream | Transformer('.//select[@id="type"]').append(
                tag.option('User List', value='user', id="user_type_option",
                           selected=selected)
            )
            stream = stream | Transformer(
                './/div[@id="field-label"]'
            ).after(
                tag.div(
                    tag.div(
                        tag.label(
                            'Included groups:',
                            for_="user-groups",
                            class_="fixed-width-label",
                        ),
                        radios,
                        select,
                        class_="field",
                    ),
                    tag.div(
                        tag.label(class_="fixed-width-label"),
                        tag.span('To have more groups listed here, check "Show by default in user drop down boxes" in ',
                                 tag.a("Manage Access and Groups",
                                       target="_blank",
                                       href=req.href.admin('access', 'access_and_groups')),
                                 ' administration page.'),
                        id="group-selection-help"
                    ),
                    manual,
                    id="user-groups",
                    class_="hidden"
                )
            )
        return stream
