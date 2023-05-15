import sys
import time
import threading

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import BooleanProperty

from kivy.lang import Builder
from kivy.uix.popup import Popup

Builder.load_string('''
<TestView>:
    okBtn:          idOK
    orientation:    "vertical"

    Label:
        text:       "Testing Blocking View"
   
    Button:
        id:         idOK
        text:       "OK"

''')

class TestView(BoxLayout):

    blocking = BooleanProperty(False)
    popup    = None

    def __init__(self, **kwargs):
        super(TestView, self).__init__(**kwargs)
        self.okBtn.bind( on_release=self.OnPress )

    def open (self):
        self.popup = Popup(title           = "Testing...",
                           content         = self,
                           size_hint       = (None, None),
                           size            = (250,150),
                           auto_dismiss    = False )
        self.popup.open()

        if self.blocking:
            if threading.current_thread().name != "MainThread":
                # NOT executing on the main thread so allow blocking
                while(self.blocking):
                    time.sleep(0.25)
                self.popup.dismiss()

    def OnPress (self, *args):
        print ("PRESSED:", args[0].text)

        if self.blocking == False:
            self.popup.dismiss()
        self.blocking = False




class TestApp(App):

    def build(self):
        root = BoxLayout(orientation='vertical')

        self.startParsing()
        return root

    def parse (self, *args):

        print ("Parsing", args[0])
        time.sleep(2.0)

        print ("Open View...")
        view = TestView( blocking=True )
        view.open()

        print ("***** AFTER OPEN EXECUTED *****")

    def startParsing (self):

        t = threading.Thread( target=self.parse, args = ["/tmp/file"] )
        t.start()

#if __name__ == "__main__":
TestApp().run()
