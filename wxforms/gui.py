import wx
import inspect
import datetime
import time
from django.forms.models import model_to_dict
from django.forms import ModelForm
from django.forms import models,fields


from django.utils.datastructures import SortedDict

class FormWidget(object):
    #this class adds django connectivity to wxControls
    basewidget = wx.TextCtrl
    def __init__(self,fieldname,model,parent):
        self.fieldname = fieldname
        self.model = model
        self.parent = parent
        self.make_widget()
        
    def make_widget(self):
        self.widget = self.basewidget(parent=self.parent,id=-1,value=str(self.model.__dict__[self.fieldname]))
        self.display = self.widget

    def get_data(self):
        data = self.widget.GetValue()
        self.model.__dict__[self.fieldname] = data
        return data
        
class DateWidget(FormWidget):
    basewidget = wx.DatePickerCtrl
    
    def make_widget(self):
        dt = self.model.__dict__[self.fieldname]
        if not dt:
            dt = datetime.datetime.now()
        self.widget = self.basewidget(parent=self.parent,id=-1,dt = wx.DateTimeFromTimeT(time.mktime(dt.timetuple())))
        self.display = self.widget
        
    def get_data(self):
        data = self.widget.GetValue().FormatISODate()
        self.model.__dict__[self.fieldname] = data
        return data

class BooleanWidget(FormWidget):
    basewidget = wx.CheckBox

class ForeignWidget(FormWidget):
    basewidget = wx.Choice
    
    def load_widget(self):
        self.widget.Clear()
        for x in self.model._meta.get_field(self.fieldname).rel.to.objects.all():
            self.widget.Append(str(x),x)
    
    def make_widget(self):
        self.display = wx.BoxSizer(wx.HORIZONTAL)
        self.widget =  self.basewidget(self.parent,id=-1)
        self.load_widget()
        self.display.Add(self.widget)
        button = wx.Button(self.parent,id=-1,label="Add")           
        self.display.Add(button)
        self.parent.Bind(wx.EVT_BUTTON, self.make_new_dialog, button)
        
    def make_new_dialog(self,event):
        dlg = FormDialog(self.model._meta.get_field(self.fieldname).rel.to())
        dlg.show_and_save()
        
    def get_data(self):
        data = self.widget.GetSelection()
        obj = self.widget.GetClientData(data)
        self.model.__class__.__dict__[self.fieldname].__set__(self.model,obj)
        return self.widget.GetString(data)

def widget_lookup(field):
    default_widgets = {
        fields.CharField:FormWidget,
        fields.DateField:DateWidget,
        fields.BooleanField:BooleanWidget,
        models.ModelChoiceField:ForeignWidget,
    }
    for cls in inspect.getmro(field.__class__):
        if cls in default_widgets.keys():
            return default_widgets[cls]
    print "using default widget for %s" % field.__class__
    return FormWidget


class FormDialog(wx.Dialog):
    def __init__(self,model_instance,form=None,parent=None,exclude=(),title=None):
        wx.Dialog.__init__(self,parent=parent,style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.title = title or model_instance.__class__.__name__
        if form:
            self.form = form
        else:
            class MForm(ModelForm):
                class Meta:
                    model = model_instance.__class__
            self.form = MForm()
        self.model = model_instance
        self.build_interface(exclude)
        # find all the fields in the parent.
        # stick them in the form in a grid sizer
        flexsizer = wx.FlexGridSizer(rows=0,cols=2,vgap=10,hgap=10)
        for v in self.interface.values():
            flexsizer.Add(wx.StaticText(self,label=v['label']),0,wx.ALIGN_RIGHT)
            flexsizer.Add(v['widget'].display,1,wx.EXPAND)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(flexsizer,1,wx.EXPAND | wx.ALL,10)
        szCmd = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        if szCmd:
            self.sizer.Add(wx.StaticLine(self),0,wx.EXPAND)
            self.sizer.Add(szCmd,0,wx.EXPAND | wx.ALL | wx.ALIGN_RIGHT,10)
            
        self.SetSizer(self.sizer)
        self.sizer.Fit(self)
        self.SetTitle(self.title)
        self.Layout()
        
    def build_interface(self,exclude):
        self.interface = SortedDict()
        i = 0
        for k,v in self.form.fields.items():
            sdvalue = {'label':"",'widget':None}
            if not exclude.__contains__(k):
                if v.label is not None:
                    sdvalue = {'label':v.label,
                               'widget': widget_lookup(v)(k,self.model,self)}
                else:
                    sdvalue = {'label':k,
                               'widget': widget_lookup(v)(k,self.model,self)}
                self.interface.insert(i, k, sdvalue)
                i+=1

    def save_model(self):
        for w in self.interface.values():
            w['widget'].get_data()
        self.model.save()

    def show_and_save(self):
        if self.ShowModal()==wx.ID_OK:
            self.save_model()

