"""recruitment URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.urls import path
from django.utils.translation import gettext_lazy as _

urlpatterns = [
    # 工作路由
    url(r"^", include("jobs.urls")),
    # 后端UI应用
    path('grappelli', include('grappelli.urls')),
    # 多语言应用,切换中、英文
    path('i18n/', include('django.conf.urls.i18n')),

    path('admin/', admin.site.urls),
    # 注册、登陆功能模块
    url(r'^accounts/', include('registration.backends.simple.urls')),

]

admin.site.site_header = _('智圣新创招聘管理系统')