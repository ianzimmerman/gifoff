from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_security import current_user, roles_required

import gifoff.models as _m


class IndexView(AdminIndexView):
    @expose('/')
    @roles_required('ADMIN')
    def index(self):
        return self.render('admin/index.html')


class CommonModelView(ModelView):
    ignore_hidden = False
    column_display_pk = True
    
    form_excluded_columns = ('date_created',
                             'date_modified')
    
    def is_accessible(self):
        return current_user.has_role('ADMIN')


class UserModelView(CommonModelView):
    form_excluded_columns = CommonModelView.form_excluded_columns + ('password',
                             'reset_password_token',
                             'confirmed_at')

    column_searchable_list = ['email', 'username']
    column_exclude_list = ['password', 'reset_password_token']

    def is_accessible(self):
        return current_user.has_role('SUPER_ADMIN')


class RoleModelView(CommonModelView):
    def is_accessible(self):
        return current_user.has_role('SUPER_ADMIN')


views = [
    dict(view=_m.User, cls=UserModelView),
    dict(view=_m.Role, cls=RoleModelView),
    dict(view=_m.Group, cls=CommonModelView),
    dict(view=_m.Challenge, cls=CommonModelView),
    dict(view=_m.Prompt, cls=CommonModelView),
    dict(view=_m.Entry, cls=CommonModelView),
    dict(view=_m.FFARating, cls=CommonModelView),
    dict(view=_m.Rating, cls=CommonModelView),
#     dict(view=_m.Tournament, cls=CommonModelView),
#     dict(view=_m.TournamentPlayers, cls=CommonModelView),
#     dict(view=_m.TournamentRound, cls=CommonModelView),
#     dict(view=_m.TournamentEntry, cls=CommonModelView),
#     dict(view=_m.TournamentVote, cls=CommonModelView),
]


admin = Admin(name="Admin", index_view=IndexView(), template_mode='bootstrap3')

for view in views:
    admin.add_view(view['cls'](view['view'], _m.db.session))
