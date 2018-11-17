#!/usr/bin/env python2
"""
En el caso de convert modificar policy.xml:
<policy domain="module" rights="read|write" pattern="{EPS,PS2,PS3,PS,PDF,XPS}" />
"""
import sys
sys.path.append('pdfminer')
import os
import io
import fnmatch
import mysql.connector
from mysql.connector import errorcode
#import subprocess
from subprocess import PIPE,Popen
import datetime

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import BytesIO


#import sys
#reload(sys)
#sys.setdefaultencoding("UTF-8")
#import site
#sys.setdefaultencoding("UTF-8")
#print sys.getdefaultencoding()

procesarPDF = 1

def pdf_to_text(path):
    manager = PDFResourceManager()
    retstr = BytesIO()
    layout = LAParams(all_texts=True)
    device = TextConverter(manager, retstr, laparams=layout)
    filepath = open(path, 'rb')
    interpreter = PDFPageInterpreter(manager, device)

    for page in PDFPage.get_pages(filepath, check_extractable=True):
        interpreter.process_page(page)

    text = retstr.getvalue()

    filepath.close()
    device.close()
    retstr.close()
    return text,len(text)


def modification_date(filename):

    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d')

def conectarMySQL():
    # Si jode insert sql grandote cambiar max_allowed_packet en my.cnf
    # o ...
    # /opt/lampp/bin/mysql -uroot -p  --max_allowed_packet=1073741824 < insert.sql
    try:
        cnx = mysql.connector.connect(user='<usuario>',
                                      password='<password>',
                                      host='localhost',
                                      database='<db>',
                                      charset='utf8',
                                      use_unicode=False)

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("mal el user/pass de MySQL")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("no existe la DB")
        else:
            print(err)
    else:
        return cnx

def getData(sql):

    cnx = conectarMySQL()
    cursor = cnx.cursor()
    cursor.execute(sql)
    cnx.close()
    return cursor.fetchall()

def insertar( sql, tipo, nombre_archivo, contenido ):

    cnx = conectarMySQL()
    cursor = cnx.cursor()
    if len(nombre_archivo) != 0:
        cursor.execute(sql, (tipo, nombre_archivo, contenido))
        cnx.commit() # aplicar
        cnx.close()
    else:
        cursor.execute(sql)
        cnx.commit() # aplicar
        cnx.close()

def decodeName(name):

    if type(name) == str: # leave unicode ones alone
        try:
            name = name.decode('utf8','ignore')
        except:
            name = name.decode('windows-1252')
    return name
        
def find_files(directory, patron):
    for root, dirs, files in os.walk(directory):
        for basename in files:
            # IMPORTANTE!!! : decode('windows-1252') porque las rutas estan en
            # utf8 en linux, pero python2 por defecto esta en ASCII -.-
            # copado si pudiese usar python3 para no hacer malabares
            #if fnmatch.fnmatch(basename.decode('windows-1252','ignore'), patron):
                #filename = os.path.join(root, basename.decode('windows-1252','ignore'))
            if fnmatch.fnmatch(basename, patron):
                filename = os.path.join(root, basename)
                yield filename #.decode('utf-8','ignore') 
                               # ya no va, porque los archivos estaban mal encodeados!
                               # renombrados corrigiendo acentos y enies


def lista_diferencia_DBFS(ruta,patron,sql):
    lista1 = []
    lista_archivosDB = []
    countinDB = 0
    for t in getData(sql):  # ->cursor.fetchall
        lista_archivosDB.append(t[0])
        #if t[0] == '/var/www/intranet/repo/documentos/sesion-8-2018/Acta 7 sesion (oct.).doc':
            #lista1.append(t[0].decode('windows-1252'))
            #print "DB tiene: "+t[0].decode('windows-1252')
        countinDB = countinDB + 1

    lista2 = []
    archivos_enFS = []
    #print "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n"

    countinFS = 0
    for nombre_archivo in find_files(ruta, patron):
        #if nombre_archivo == '/var/www/intranet/repo/documentos/sesion-8-2018/Acta 7 sesion (oct.).doc':
            #lista2.append(nombre_archivo)
            #print "FS TIENE: "+nombre_archivo
        archivos_enFS.append(nombre_archivo)
        countinFS = countinFS + 1

    #diff_temp = []
    #diff_temp2 = []
    #diff_temp = list(set(lista1) - set(lista2))
    #diff_temp2 = list(set(lista2) - set(lista1))
    """
    print "1-2:"+ruta
    for n in diff_temp:
        print "[ DB -FS ] "+ruta+" ->"+n

    print "2-1:"+ruta
    for n in diff_temp2:
        print "[ FS - DB ] "+ruta+" ->"+n
    """  
    diffrev = []
    diffrev = list(set(lista_archivosDB) - set(archivos_enFS))
   
    if diffrev:
       print "Archivos en DB que ya no estan en FS: "
    for n in diffrev:
        print "     [DB-FS]: "+n   

    diff = []
    diff = list(set(archivos_enFS) - set(lista_archivosDB))

    return diff, countinDB, countinFS


def procesar_pdf(diff, procesarPDF, tipo):

    for nombre_archivo in diff:
        print "-> Indexando "+nombre_archivo

        if procesarPDF == 1:
            os.system('cp "'+nombre_archivo+'" tmp.pdf')
            #os.system('convert -density 300 tmp.pdf -depth 8 -strip -background white -alpha off file.tiff')
            #gs -dBATCH -dNOPAUSE -sDEVICE=txtwrite -sOutputFile=1.txt res-01404-2018.pdf
            # tiffg4 muy matricial, aun con r600 sale cualquier banana. Usando tiff no B/N, con resolucion no muy alta para
            # evitar archivo inmenso
            #os.system('gs -dNOPAUSE -r600 -dINTERPOLATE  -dNumRenderingThreads=8 -sDEVICE=tiffg4 -o file.tiff tmp.pdf')
            #os.system('convert -density 300 "'+nombre_archivo+'" -depth 8 -strip -background white -alpha off file.tiff')
            try:
                txt,longitud = pdf_to_text("tmp.pdf")
                #print "LONGITUD:  "+str(longitud)
            except AttributeError:
                print "Excepcion AttributeError de  pdfminer"
                pass
            except:
                print "Excepcion en pdfminer"
                pass
            try: 
                 if longitud < 100:
                     print "Conversion & OCR..."
                     os.system('gs -dNOPAUSE -dINTERPOLATE  -r150 -dGraphicsAlphaBits=4 -dNumRenderingThreads=8 -sDEVICE=tiff32nc  -o file.tiff tmp.pdf > /dev/null 2>&1')
                     os.system("tesseract file.tiff ocr -l spa > /dev/null 2>&1 ")
                     ocr_txt = io.open("ocr.txt", "r", encoding="utf-8")
                     contenido = ocr_txt.read()
                     contenido = " ".join(contenido.split())
                 else:
                     contenido = txt
                     #print "PDF CON TEXTO..." 
            except: 
                print "Excepcion en gs o tesseract"
                pass
            sql =  "INSERT IGNORE INTO ocr (tipo,archivo,contenido) VALUES ( %s , %s , %s )"
            insertar(sql, tipo, nombre_archivo, contenido)
            os.system("rm -f file.tiff && rm -f ocr.txt && rm -f tmp.pdf && find /tmp -maxdepth 1 -type f -name 'magick-*' -delete")
            #raw_input("Press Enter to continue...")

def procesar_words(diff, tipo):

    for nombre_archivo in diff:
        # cuidado al imprimir, con nohup tira error por bad encoding. Derecho sin nohup no tira error :O
        print "-> "+nombre_archivo
        #arch = subprocess.check_output("php extraertxt_de_docs.php?"+nombre_archivo, shell=True);
        # subprocess.check_output(["... no funca, porque es python < 2.7 :(
        #Popen(['gs', '-dBATCH','-dNOPAUSE','-sDEVICE=txtwrite','-sOutputFile=a.txt','/tmp/res-01404-2018.pdf'], stdout=PIPE,stderr=None)
        contenidoDOC = Popen(['php', 'extraertxt_de_docs.php', nombre_archivo], stdout=PIPE)
        sql =  '''INSERT IGNORE INTO ocr (tipo,archivo,contenido) VALUES ( %s , %s , %s )'''
        insertar(sql, tipo, nombre_archivo, contenidoDOC.communicate()[0])


try: 
    # Y LUEGO REVEER los que se guardaron vacios-> WHERE LENGTH(contenido)='0'

    ###################### RESOLUCIONES  FI (.DOC*)  #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='1' AND (nombre LIKE '%.doc' OR nombre LIKE '%.docx') "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/institucional/legislacion/facultad/resoluciones','*.do*[xc]',sql)

    print "\n\n---------------archivos de RESOLUCIONES FI que faltan procesar  *.DOC* -----------------:"


    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)


    procesar_words(diff,'1')



    ###################### RESOLUCIONES FI  (.PDF*)  #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='1' AND nombre LIKE '%.pdf' "
    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/institucional/legislacion/facultad/resoluciones/','*.pdf',sql)

    print "\n\n----------------archivos de RESOLUCIONES FI que faltan procesar  *.PDF -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_pdf(diff, procesarPDF,'1')



    ###################### ORDENANZAS FI (.DOC*)  #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='2' AND (nombre LIKE '%.doc' OR nombre LIKE '%.docx') "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/institucional/legislacion/facultad/ordenanzas','*.do*[xc]',sql)

    print "\n\n---------------archivos de ORDENANZAS FI que faltan procesar  *.DOC* -----------------:"


    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)


    procesar_words(diff,'2')



    ###################### ORDENANZAS FI  (.PDF*)  #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='2' AND nombre LIKE '%.pdf' "
    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/institucional/legislacion/facultad/ordenanzas/','*.pdf',sql)

    print "\n\n----------------archivos de ORDENANZAS FI que faltan procesar  *.PDF -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_pdf(diff, procesarPDF,'2')



    ###################### DIGESTO (.DOC*)  #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='3' AND (nombre LIKE '%.doc' OR nombre LIKE '%.docx') "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/intranet/repo/digesto','*.do*[xc]',sql)

    print "\n\n---------------archivos de DIGESTO que faltan procesar  *.DOC* -----------------:"


    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)


    procesar_words(diff,'3')



    ###################### DIGESTO (.PDF*)  #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='3' AND nombre LIKE '%.pdf' "
    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/intranet/repo/digesto','*.pdf',sql)

    print "\n\n----------------archivos de DIGESTO que faltan procesar  *.PDF -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_pdf(diff, procesarPDF,'3')



    ###################### DOC CONSEJO (.DOC*) #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='4' AND (nombre LIKE '%.doc' OR nombre LIKE '%.docx') "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/intranet/repo/documentos','*.do*[xc]',sql)

    print "\n\n----------------archivos de DOC CONSEJO que faltan procesar *.DOC* -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_words(diff,'4')


    ###################### DOC CONSEJO (.PDF) #######################

    sql = " SELECT archivo,id FROM ocr WHERE tipo='4' AND nombre LIKE '%.pdf' "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/intranet/repo/documentos','*.pdf',sql)

    print "\n\n----------------archivos de DOC CONSEJO que faltan procesar *.PDF -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_pdf(diff, procesarPDF,'4')

    ###################### RESOL UNLP (.PDF) #######################

    sql = " SELECT archivo,id FROM ocr WHERE tipo='5' AND nombre LIKE '%.pdf' "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/institucional/legislacion/unlp/resoluciones','*.pdf',sql)

    print "\n\n----------------archivos de RESOL UNLP que faltan procesar *.PDF -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_pdf(diff, procesarPDF,'5')


    ###################### ORD UNLP (.PDF) #######################

    sql = " SELECT archivo,id FROM ocr WHERE tipo='6' AND nombre LIKE '%.pdf' "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/institucional/legislacion/unlp/ordenanzas','*.pdf',sql)

    print "\n\n----------------archivos de ORD UNLP que faltan procesar *.PDF -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_pdf(diff, procesarPDF,'6')


    ###################### LEGISLACION NACION (.PDF) #######################

    sql = " SELECT archivo,id FROM ocr WHERE tipo='7' AND nombre LIKE '%.pdf' "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/institucional/legislacion/nacional','*.pdf',sql)

    print "\n\n----------------archivos de LEGISLACION -> NACIONAL que faltan procesar *.PDF -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_pdf(diff, procesarPDF,'7')


    ###################### CONCURSOS (.DOC*) #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='8' AND (nombre LIKE '%.doc' OR nombre LIKE '%.docx') "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/administracion/concursos/archivos','*.do*[xc]',sql)

    print "\n\n----------------archivos de CONCURSOS que faltan procesar *.DOC* -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_words(diff,'8')


    ###################### CONCURSOS (.PDF) #######################

    sql = " SELECT archivo,id FROM ocr WHERE tipo='8' AND nombre LIKE '%.pdf' "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/administracion/concursos/archivos','*.pdf',sql)

    print "\n\n----------------archivos de CONCURSOS que faltan procesar *.PDF -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_pdf(diff, procesarPDF,'8')


    ###################### PERSONAL (.DOC*) #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='9' AND (nombre LIKE '%.doc' OR nombre LIKE '%.docx') "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/administracion/personal/archivos','*.do*[xc]',sql)

    print "\n\n----------------archivos de PERSONAL que faltan procesar *.DOC* -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_words(diff,'9')


    ###################### PERSONAL (.PDF) #######################

    sql = " SELECT archivo,id FROM ocr WHERE tipo='9' AND nombre LIKE '%.pdf' "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/administracion/personal/archivos','*.pdf',sql)

    print "\n\n----------------archivos de PERSONAL que faltan procesar *.PDF -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_pdf(diff, procesarPDF,'9')


    ###################### DOCENTES (.DOC*) #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='10' AND (nombre LIKE '%.doc' OR nombre LIKE '%.docx') "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/docentes/archivos','*.do*[xc]',sql)

    print "\n\n----------------archivos de DOCENTES que faltan procesar *.DOC* -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_words(diff,'10')


    ###################### DOCENTES (.PDF) #######################

    sql = " SELECT archivo,id FROM ocr WHERE tipo='10' AND nombre LIKE '%.pdf' "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/sitio/docentes/archivos','*.pdf',sql)

    print "\n\n----------------archivos de DOCENTES que faltan procesar *.PDF -----------------:"

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    procesar_pdf(diff, procesarPDF,'10')



    # Actualizar y rellenar otros campos:

    sql = " SELECT archivo,id FROM ocr WHERE fecha IS NULL "
    insertar("UPDATE ocr SET nombre=SUBSTRING_INDEX(archivo,'/',-1)", "", "","")

    for t in getData(sql):
        d = modification_date(t[0])
        #print "id: "+str(t[1])+" ->"+d
        insertar("UPDATE ocr SET fecha='"+d+"' WHERE id='"+str(t[1])+"'", "", "","")
except:
    print "Error inesperado, eliminando posibles temporales..."
    os.system("rm -f file.tiff && rm -f ocr.txt && rm -f tmp.pdf") # && find /tmp -maxdepth 1 -type f -name 'magick-*' -delete")    
    #raise
