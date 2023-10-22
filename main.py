import kivy 
import time                                                                                    
from kivy.app import App                                                                        
from kivy.lang import Builder                                                                   
from kivy.utils import platform                                                                 
from kivy.uix.widget import Widget                                                              
from kivy.clock import Clock                                                                    
import os                                     
from PIL import Image
from threading import Thread
from flask import Flask,jsonify,request,make_response
from parse_cr3 import MainParser
from sqlwrap import Db

import urllib.parse
import hashlib
import io
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
import json

def h(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()


is_android=False
if kivy.utils.platform == 'android':
    is_android=True
    from jnius import autoclass,cast                                                                 
    from android.runnable import run_on_ui_thread   
    from android import activity, mActivity
    from jnius import autoclass   
    WebView = autoclass('android.webkit.WebView')
    WebViewClient = autoclass('android.webkit.WebViewClient')
    from android.storage import app_storage_path, primary_external_storage_path, secondary_external_storage_path     
    Intent = autoclass('android.content.Intent')
    DocumentsContract = autoclass('android.provider.DocumentsContract')
    Document = autoclass('android.provider.DocumentsContract$Document')
    Uri=autoclass('android.net.Uri')
else:
    def a(arg):return None
    run_on_ui_thread=a



webview=None

@run_on_ui_thread
def create_webview(*args):
    global webview
    webview = WebView(mActivity)
    webview.getSettings().setJavaScriptEnabled(True)
    webview.setHorizontalScrollBarEnabled(False)
    webview.getSettings().setUseWideViewPort(True)
    wvc = WebViewClient();
    webview.setWebViewClient(wvc);
    mActivity.setContentView(webview)
    webview.loadUrl('http://127.0.0.1:8088/index.html')

@run_on_ui_thread
def signal(command=None,payload={}):
    j=json.dumps({'command':command,'payload':payload})
    webview.loadUrl("javascript:indata('"+j+"');")



class Wv(Widget):
    def __init__(self, **kwargs):                                                               
        super(Wv, self).__init__(**kwargs) 
                                         
                                                                                                



        
                                                                                                
class ServiceApp(App):    

    REQUEST_CODE = 42 # unique request ID
    REQUEST_CODE_COPY=43
 
    def set_intent(self,*args):
        intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)        
        mActivity.startActivityForResult(intent, self.REQUEST_CODE)  


    def set_intent_copy(self,*args):
        intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)        
        mActivity.startActivityForResult(intent, self.REQUEST_CODE_COPY)         

    def intent_callback(self, requestCode, resultCode, intent):
        if requestCode == self.REQUEST_CODE:
            msg = ""
            root_uri = intent.getData()
            DocumentsContract = autoclass('android.provider.DocumentsContract')
            Document = autoclass('android.provider.DocumentsContract$Document')
            root_id = DocumentsContract.getTreeDocumentId(root_uri)
            children = DocumentsContract.buildChildDocumentsUriUsingTree(root_uri,root_id)
            contentResolver = mActivity.getContentResolver();
            info = [Document.COLUMN_DISPLAY_NAME,Document.COLUMN_DOCUMENT_ID]
            c = contentResolver.query(children, info, None, None, None);

            while c.moveToNext():

                name = str(c.getString(0))
                myFileUri = DocumentsContract.buildDocumentUriUsingTree(root_uri,c.getString(1) )
                if name.lower().endswith('.cr3'):
                    self.files.append(myFileUri)
            c.close()
            signal(command='start_scan',payload={'count':0,'all':len(self.files)})
            self.db.clear()
            Thread(target=self.startscan).start() 

        if requestCode == self.REQUEST_CODE_COPY:
            root_uri = intent.getData()
            DocumentsContract = autoclass('android.provider.DocumentsContract')
            Document = autoclass('android.provider.DocumentsContract$Document')
            root_id = DocumentsContract.getTreeDocumentId(root_uri)
            children = DocumentsContract.buildChildDocumentsUriUsingTree(root_uri,root_id)
            self.copy_to = children


            contentResolver = mActivity.getContentResolver();
            info = [Document.COLUMN_DISPLAY_NAME,Document.COLUMN_DOCUMENT_ID]
            c = contentResolver.query(children, info, None, None, None);
            self.target_file_list=[]
            while c.moveToNext():
                self.target_file_list.append(str(c.getString(0)))


            Thread(target=self.start_copy).start()             



    def start_copy(self,*args):
        DocumentsContract = autoclass('android.provider.DocumentsContract')
        contentResolver = mActivity.getContentResolver()




        for n,x in enumerate(self.copy_items):
            fname=x.toString().split('%2F')[-1]
            if fname in self.target_file_list:continue

            docStream = mActivity.getContentResolver().openInputStream(x)
            indoc = docStream.readAllBytes()
            docStream.close()


            newdoc=DocumentsContract.createDocument(contentResolver,self.copy_to,'image/x-canon-cr3',fname)
            out=contentResolver.openOutputStream( newdoc, "w")
            out.write(indoc)
            out.close()
            if is_android:
                signal(command='copy_action',payload={'count':n+1,'all':len(self.copy_items)})
        signal(command='copy_end',payload={})




    def run_flask(self,*args):
        self.app.run(port=8088)



    def flask_action(self,j=None):
        data={}
        content = request.json
        if content['action']=='startfolder':
            self.only_rated=content['data']
            if is_android:
                self.set_intent()
            else:
                self.files=os.listdir('../android_in/')
                self.db.clear()
                self.startscan()    
        if content['action']=='startscan':
            self.db.clear()
            self.startscan()
        if content['action']=='get_all':
            data['all_photos']=self.db.get_all()
        if content['action']=='set':
            self.db.set(data=json.loads(content['data']))
        if content['action']=='filter':
            dt=content['data']
            out=[]
            for d in self.db.get_all():
                if d[1] and 'ch' in dt:out.append(d)
                if d[2]==1 and 'r1' in dt:out.append(d)
                if d[2]==2 and 'r2' in dt:out.append(d)
                if d[2]==3 and 'r3' in dt:out.append(d)
                if d[2]==4 and 'r4' in dt:out.append(d)
                if d[2]==5 and 'r5' in dt:out.append(d)
            data['all_photos']=out    
        if content['action']=='export_app':
            ArrayList = autoclass('java.util.ArrayList')
            alist=ArrayList()
            for item in content['data']:
                for x in self.files:
                    if is_android and item[0]==h(x.toString()):
                        alist.add(x)
            intent = Intent()
            intent.setAction(Intent.ACTION_SEND_MULTIPLE)
            intent.putParcelableArrayListExtra(Intent.EXTRA_STREAM, alist);
            intent.setType("*/*")
            String = autoclass('java.lang.String')
            shareIntent = Intent.createChooser(intent, String(f'Export cr3 files'))
            mActivity.startActivity(shareIntent)
              

        if content['action']=='export_copy':
            self.copy_items=[]
            for item in content['data']:
                for x in self.files:
                    if is_android and item[0]==h(x.toString()):
                        self.copy_items.append(x)
            self.set_intent_copy()





        return jsonify(data)

    def startscan(self,*args):
        for count,file in enumerate(self.files):
            if is_android:
                docStream = mActivity.getContentResolver().openInputStream(file)
                intVal = bytes(docStream.readNBytes(1*1024*1024))
                file=file.toString()
            else:

                intVal=open('../android_in/'+file,'rb').read(1*1024*1024)
            m=MainParser(intVal)

            if (not self.only_rated) or (self.only_rated and m.rating>0):
                self.db.add([h(file),0,m.rating,m.orientation,m.thumb_img])
            if is_android and count%10==0:
                signal(command='start_scan',payload={'count':count+1,'all':len(self.files)})
        self.db.end_add()
        if is_android:
            signal(command='end_scan',payload=self.db.get_all())

    def flask_thumb(self):
        page = request.args.get('path',type = str)
        image_binary = self.db.get_thumb(page)
        response = make_response(image_binary)
        response.headers.set('Content-Type', 'image/jpeg')
        response.headers.set(
            'Content-Disposition', 'attachment', filename='%s.jpg' % page)
        return response

    def flask_full(self):
        page = request.args.get('path',type = str)
        if is_android:
            for x in self.files:
                if page==h(x.toString()):
                    u=x
            docStream = mActivity.getContentResolver().openInputStream(u)
            intVal = bytes(docStream.readNBytes(3*1024*1024))
        else:
            for x in self.files:
                if page==h(x):
                    page=x
            intVal=open('../android_in/'+page,'rb').read(3*1024*1024)
        m=MainParser(intVal)



        image_binary = m.full_size

        if m.orientation!=1:
            i=io.BytesIO(image_binary)
            img=Image.open(i)
            img=img.rotate(90, expand=True)
            i2=io.BytesIO()
            img.save(i2,format='jpeg',quality=85)
            i2.seek(0)
            image_binary=i2.read()

        response = make_response(image_binary)
        response.headers.set('Content-Type', 'image/jpeg')
        response.headers.set(
            'Content-Disposition', 'attachment', filename='%s.jpg' % page)
        return response      

    def on_start(self):
        from kivy.base import EventLoop
        EventLoop.window.bind(on_keyboard=self.hook_keyboard)

    def hook_keyboard(self, window, key, *largs):
        print('key>',key)
        if key == 27:
            return True
        return True

    def build(self):
        self.files=[]
        if is_android:
            activity.bind(on_activity_result=self.intent_callback)

        self.db=Db()
        self.app = Flask(__name__,static_url_path='', static_folder='static')
        self.app.add_url_rule('/action', view_func=self.flask_action,methods=['GET', 'POST'])
        self.app.add_url_rule('/get_thumb/', view_func=self.flask_thumb,methods=['GET'])        
        self.app.add_url_rule('/get_full/', view_func=self.flask_full,methods=['GET'])   
        Thread(target=self.run_flask).start()                                              
        if is_android:
            Clock.schedule_once(create_webview, 0)                                                                           
        return None                                                                           
                                                                                                
if __name__ == '__main__':                                                                      
    ServiceApp().run()