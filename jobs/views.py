from django.shortcuts import render
from django.http import HttpResponse
from django.http import Http404
from django.template import loader

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.detail import DetailView

from jobs.models import Job, Resume
from jobs.models import Cities, JobTypes
from jobs.forms import ResumeForm
from django.views.generic.edit import CreateView
from django.http import HttpResponseRedirect

from django import template

import logging

logger = logging.getLogger(__name__)

register = template.Library()


def joblist(request):
    job_list = Job.objects.order_by('job_type')
    context = {'joblist': job_list}

    for job in job_list:
        print(type(job))
        print(job.job_type)
        job.city_name = Cities[job.job_city][1]
        job.job_type = JobTypes[job.job_type][1]
    print(job_list)
    return render(request, 'joblist.html', context)


def detail(request, job_id):
    try:
        job = Job.objects.get(pk=job_id)
        job.city_name = Cities[job.job_city][1]
        logger.info('job retrieved from db :%s' % job_id)
    except Job.DoesNotExist:
        raise Http404('Job does not exit.')
    return render(request, 'job.html', {'job': job})


def detail_resume(request, resume_id):
    '''
        直接返回  HTML 内容的视图 （这段代码返回的页面有 XSS 漏洞，能够被攻击者利用）
        演示XSS跨站请求攻击
    '''
    try:
        resume = Resume.objects.get(pk=resume_id)
        content = "name: %s <br>  introduction: %s <br>" % (resume.username, resume.candidate_introduction)
        return HttpResponse(content)
    except Resume.DoesNotExist:
        raise Http404("resume does not exist")


class ResumeDetailView(DetailView):
    """   简历详情页    """
    model = Resume
    template_name = 'resume_detail.html'


class ResumeCreateView(LoginRequiredMixin, CreateView):
    """    简历职位页面  """
    template_name = 'resume_form.html'
    success_url = '/joblist/'
    model = Resume
    fields = ["username", "city", "phone",
              "email", "apply_position", "gender",
              "bachelor_school", "master_school", "major", "degree", "picture", "attachment",
              "candidate_introduction", "work_experience", "project_experience"]

    # def post(self, request, *args, **kwargs):
    #     form = ResumeForm(request.POST, request.FILES)
    #     if form.is_valid():
    #         # <process form cleaned data>
    #         form.save()
    #         return HttpResponseRedirect(self.success_url)
    #
    #     return render(request, self.template_name, {'form': form})
    #
    ### 从 URL 请求参数带入默认值
    def get_initial(self):
        initial = {}
        for x in self.request.GET:
            initial[x] = self.request.GET[x]
        return initial

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.applicant = self.request.user
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())
