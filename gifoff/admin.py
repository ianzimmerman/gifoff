from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_security import current_user, roles_required

from .models import db, User, Role


class IndexView(AdminIndexView):
    @expose('/')
    @roles_required('ADMIN')
    def index(self):
        return self.render('admin/index.html')


class CommonModelView(ModelView):
    form_excluded_columns = ('date_created',
                             'date_modified')
    column_display_pk = True

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
    dict(view=User, cls=UserModelView),
    dict(view=Role, cls=RoleModelView),
]


admin = Admin(name="Admin", index_view=IndexView(), template_mode='bootstrap3')

for view in views:
    admin.add_view(view['cls'](view['view'], db.session))
