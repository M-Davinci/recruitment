from django.contrib import admin
from django.contrib import messages
from django.utils.safestring import mark_safe

from django.http import HttpResponse
from django.db.models import Q

from jobs.models import Resume
from interview import candidate_field as cf
from .tasks import send_dingtalk_message
import csv
import logging
from datetime import datetime

from interview.models import Candidate

logger = logging.getLogger(__name__)

# 导出的字段
exportable_fields = (
    'username', 'city', 'phone', 'bachelor_school', 'master_school', 'degree', 'first_result', 'first_interviewer_user',
    'second_result', 'second_interviewer_user', 'hr_result', 'hr_score', 'hr_remark', 'hr_interviewer_user')


# 通知一面面试官面试
def notify_interviewer(modeladmin, request, queryset):
    candidates = ""
    interviewers = ""
    print(queryset)
    for obj in queryset:
        candidates = obj.username + ";" + candidates
        if obj.first_interviewer_user:
            interviewers = obj.first_interviewer_user.username + ";" + interviewers
        else:
            return messages.add_message(request, messages.INFO, '请先添加面试官！')

    # 这里的消息发送到钉钉， 或者通过 Celery 异步发送到钉钉,一个参数是通知信息，第二参数是，通知类别，第三个参数是@群里组员
    send_dingtalk_message.delay("候选人 %s 进入面试环节，亲爱的面试官，请准备好面试： %s" % (candidates, interviewers), '面试通知', ['18788879076'])
    # send_dingtalk_message.delay("候选人 %s 进入面试环节，亲爱的面试官，请准备好面试： %s" % (candidates, interviewers) )
    messages.add_message(request, messages.INFO, '已经成功发送面试通知')


# define export action
def export_model_as_csv(modeladminm, request, queryset):
    response = HttpResponse(content_type='text/csv')
    field_list = exportable_fields
    response['Content-Disposition'] = 'attachment; filename=%s-list-%s.csv' % (
        'recruitment-candidates',
        datetime.now().strftime('%Y-%m-%d-%H-%M-%S'),
    )
    # 写入表头
    writer = csv.writer(response)
    writer.writerow(
        [queryset.model._meta.get_field(f).verbose_name for f in field_list],
    )

    for obj in queryset:
        ## 单行的记录（各个字段的值）， 根据字段对象，从当前实例 (obj) 中获取字段值
        csv_line_values = []
        for field in field_list:
            field_object = queryset.model._meta.get_field(field)
            field_value = field_object.value_from_object(obj)
            csv_line_values.append(field_value)
        writer.writerow(csv_line_values)

    logger.error(" %s has exported %s candidate records" % (request.user.username, len(queryset)))
    return response


notify_interviewer.short_description = u'通知面试官'
export_model_as_csv.short_description = u'导出为CSV文件'
export_model_as_csv.allowed_permissions = ('export',)


# 候选人管理类
class CandidateAdmin(admin.ModelAdmin):
    exclude = ('creator', 'created_date', 'modified_date')

    # 执行的动作
    actions = (export_model_as_csv, notify_interviewer,)

    # 当前用户是否有导出权限：
    def has_export_permission(self, request):
        opts = self.opts
        return request.user.has_perm('%s.%s' % (opts.app_label, "export"))

    # 展示的字段
    list_display = (
        'username', 'city', 'bachelor_school', 'get_resume', 'first_score', 'first_result', 'first_interviewer_user',
        'second_result', 'second_interviewer_user', 'hr_score', 'hr_result', 'hr_interviewer_user',
    )

    # 右侧筛选条件
    list_filter = (
        'city', 'first_result', 'second_result', 'hr_result', 'first_interviewer_user', 'second_interviewer_user',
        'hr_interviewer_user')

    # 查询字段
    search_fields = ('username', 'phone', 'email', 'bachelor_school')

    # 列表页排序字段
    ordering = ('hr_result', 'second_result', 'first_result',)

    # 定义一个方法，插入一个字段，可以查看简历的来源
    def get_resume(self, obj):
        if not obj.phone:
            return ""
        resumes = Resume.objects.filter(phone=obj.phone)
        if resumes and len(resumes) > 0:
            return mark_safe(u'<a href="/resume/%s" target="_blank">%s</a' % (resumes[0].id, "查看简历"))
        return ""

    get_resume.short_description = '查看简历'
    get_resume.allow_tags = True

    # 一面面试官仅填写一面反馈， 二面面试官可以填写二面反馈
    def get_fieldsets(self, request, obj=None):
        group_names = self.get_group_names(request.user)

        if 'interviewer' in group_names and obj.first_interviewer_user == request.user:
            return cf.default_fieldsets_first
        if 'interviewer' in group_names and obj.second_interviewer_user == request.user:
            return cf.default_fieldsets_second
        return cf.default_fieldsets

    # 对于非管理员，非HR，获取自己是一面面试官或者二面面试官的候选人集合
    def get_queryset(self, request):  # show data only owned by the user
        qs = super(CandidateAdmin, self).get_queryset(request)

        group_names = self.get_group_names(request.user)
        if request.user.is_superuser or 'hr' in group_names:
            return qs
        return Candidate.objects.filter(
            Q(first_interviewer_user=request.user) | Q(second_interviewer_user=request.user))

    def get_list_editable(self, request):
        # 获取可编辑的字段，如果是超级管理员或者hr可以有编辑的权限
        group_names = self.get_group_names(request.user)
        if request.user.is_superuser or 'hr' in group_names:
            return ('first_interviewer_user', 'second_interviewer_user',)
        return ()

    def get_changelist_instance(self, request):
        """
        override admin method and list_editable property value
        with values returned by our custom method implementation.
        """
        self.list_editable = self.get_list_editable(request)
        return super(CandidateAdmin, self).get_changelist_instance(request)

    def get_group_names(self, user):
        group_names = []
        for g in user.groups.all():
            group_names.append(g.name)
        return group_names

    def get_readonly_fields(self, request, obj):
        # 如果登陆用户的权限是面试官，则面试官为只读，没有修改面试官的权限
        group_names = self.get_group_names(request.user)

        if 'interviewer' in group_names:
            logger.info("interviewer is in user's group for %s" % request.user.username)
            # 返回只读的字段
            return ('first_interviewer_user', 'second_interviewer_user',)
        return ()


admin.site.register(Candidate, CandidateAdmin)
