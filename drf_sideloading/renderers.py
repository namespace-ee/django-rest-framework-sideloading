from rest_framework.renderers import BrowsableAPIRenderer


class BrowsableAPIRendererWithoutForms(BrowsableAPIRenderer):
    def get_context(self, *args, **kwargs):
        context = super(BrowsableAPIRendererWithoutForms, self).get_context(*args, **kwargs)
        context["display_edit_forms"] = False
        return context

    def show_form_for_method(self, view, method, request, obj):
        return False

    def get_rendered_html_form(self, data, view, method, request):
        return ""
