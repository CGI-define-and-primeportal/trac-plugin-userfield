from trac.core import *
from trac.perm import PermissionSystem
from trac.web.api import IRequestFilter, ITemplateStreamFilter
from trac.web.chrome import (ITemplateProvider, add_script, add_script_data,
                             add_stylesheet)
from trac.ticket.api import ITicketManipulator
from trac.ticket.web_ui import TicketModule
from trac.config import Option, IntOption, BoolOption, ListOption

from trac.web.session import DetachedSession

from genshi.builder import tag
from genshi.filters.transform import Transformer

from simplifiedpermissionsadminplugin.model import Group

import time
from itertools import chain
from traceback import format_exc
import re

class UserFieldModule(Component):
    """A module providing a user custom field based on user group."""

    match_req = ListOption('userfield', 'match_request', default='[]',
        doc='Additional request paths to match (use input class="user-field")')

    implements(ITicketManipulator, ITemplateStreamFilter)

    # ITemplateStreamFilter methods
    def filter_stream(self, req, method, filename, stream, data):

        apply_filter = False

        selector = ['.user-field']
        if filename == 'ticket.html':
            selector.extend('#field-' + n for n in self._user_fields())
            apply_filter = True
        else:
            patterns = chain(('/newticket',
                              '/ticket',
                              '/simpleticket',
                              '/timeline'),
                             self.match_req
                            )

            apply_filter = req.path_info.startswith(tuple(patterns))

        if not apply_filter:
            return stream

        perms = sorted(PermissionSystem(self.env).get_all_permissions())
        grs = Group.groupsBy(self.env)
        groups = {}
        for gr in grs:
            group = Group(self.env, gr)
            groups[gr] = {}
            groups[gr]['label'] = group.label
            if not group.external_group:
                groups[gr]['members'] = []
                for subject, permission in perms:
                    if permission == gr and subject not in grs:
                        session = DetachedSession(self.env, subject)
                        session.update(username=subject)
                        groups[gr]['members'].append(session)

        add_script_data(req, {'userfield_selector': ','.join(selector),
                              'userGroups': groups,
                             })
        add_script(req, 'userfield/js/userfield.js')

        return stream

    # ITicketManipulator methods
    def prepare_ticket(self, req, ticket, fields, actions):
        pass

    def validate_ticket(self, req, ticket): # dmy mdy ymd
        for field in self._user_fields():
            field_layout_config = TicketModule(self.env).field_layout_controller.get_layout_for_field_on_type(ticket['type'],
                                                                                                              field)
            if field_layout_config:
                return []

    # Internal methods
    def _user_fields(self):
        # XXX: Will this work when there is no ticket-custom section? <NPK>
        for key, value in self.config['ticket-custom'].options():
            if len(key.split(".")) == 1 and value == "user":
                yield key.split('.', 1)[0]


class CustomFieldAdminTweak(Component):
    implements(ITemplateStreamFilter, IRequestFilter, ITemplateProvider)

    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('userfield', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []

    def pre_process_request(self, req, handler):
        if req.method == "POST" and req.path_info.startswith(u"/admin/ticket/customfields"):
            if req.args.get('type') == 'user':
                if req.args.get("all_or_selection") == "all":
                    self.config.set('ticket-custom', '%s.groups'%(req.args.get('name')), '*')
                else :
                    user_groups = req.args.get("user_groups", [])
                    if isinstance(user_groups, list):
                        user_groups = "|".join(user_groups)

                    self.config.set('ticket-custom', '%s.groups'%(req.args.get('name')), user_groups)
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
        invalid_edit = re.search("[^a-zA-Z0-9]", edit_name)

        currently_editing = edit_name and not invalid_edit

        if currently_editing:
            groups = self.config.get("ticket-custom", edit_name + ".groups").split("|")
        else:
            groups = []

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
                        "Selection",
                        tag.input(
                            type="radio",
                            value="selection",
                            name="all_or_selection",
                            checked=(None if "*" in groups else "checked"),
                        )
                    ))

        for sid in Group.groupsBy(self.env):
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
                tag.option('User List', value='user', id="user_type_option", selected = selected)
            )
            stream = stream | Transformer(
                './/div[@id="field-label"]'
            ).after(
                tag.div(
                    tag.label(
                        'Included Groups',
                        for_="user-groups",
                        class_="fixed-width-label",
                    ),
                    radios,
                    select,
                    class_="field hidden",
                    id="user-groups"
                )
            )
        return stream
