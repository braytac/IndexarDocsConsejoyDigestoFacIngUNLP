#!/usr/bin/env python2
"""
Docstring para que pylint no joda
recordar en mysql setear max_allowed_packet = 100M para poder hacer insert
sys.getdefaultencoding() devuelve default encoding para python ASCII,
pero el FS en linux es utf8 -> se descajetan los nombres de archivo
agregar esto, o manejar senales:
try:
    while True:
      print 1
except KeyboardInterrupt:
    print "test"
,tener en cuenta terminar tesseract y convert si estan a mitad de camino
Si en alguna distro tira algo como:

convert: attempt to perform an operation not allowed by the security policy `PDF' @ error/module.c/OpenModule/1257.
convert: no decode delegate for this image format `PDF' @ error/constitute.c/ReadImage/556.
convert: no images defined `file.tiff' @ error/convert.c/ConvertImageCommand/3288.

, modificar policy.xml:

<policy domain="module" rights="read|write" pattern="{EPS,PS2,PS3,PS,PDF,XPS}" />

"""
import os
import io
import fnmatch
import mysql.connector
from mysql.connector import errorcode
#import subprocess
from subprocess import PIPE,Popen
import datetime

#import sys
#reload(sys)
#sys.setdefaultencoding("UTF-8")
#import site
#sys.setdefaultencoding("UTF-8")
#print sys.getdefaultencoding()

procesarPDF = 1

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

def insertar( sql, nombre_archivo, contenido ):

    cnx = conectarMySQL()
    cursor = cnx.cursor()
    if len(nombre_archivo) != 0:
        cursor.execute(sql, (nombre_archivo, contenido))
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

    lista_archivosDB = []
    countinDB = 0
    for t in getData(sql):  # ->cursor.fetchall
        lista_archivosDB.append(t[0])
        #print t[0]
        countinDB = countinDB + 1
    archivos_enFS = []
    #print "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n"

    countinFS = 0

    for nombre_archivo in find_files(ruta, patron):
        archivos_enFS.append(nombre_archivo)
        countinFS = countinFS + 1

    diff = []
    diff = list(set(archivos_enFS) - set(lista_archivosDB))
    return diff, countinDB, countinFS


def procesar_pdf(diff):

    for nombre_archivo in diff:
        print "-> "+nombre_archivo

        if procesarPDF == 1:
            os.system('cp "'+nombre_archivo+'" tmp.pdf')
            #os.system('convert -density 300 tmp.pdf -depth 8 -strip -background white -alpha off file.tiff')
            os.system('gs -dNOPAUSE -dINTERPOLATE  -r150 -dGraphicsAlphaBits=4 -dNumRenderingThreads=8 -sDEVICE=tiff32nc  -o file.tiff tmp.pdf')
            # tiffg4 muy matricial, aun con r600 sale cualquier banana. Usando tiff no B/N, con resolucion no muy alta para
            # evitar archivo inmenso
            #os.system('gs -dNOPAUSE -r600 -dINTERPOLATE  -dNumRenderingThreads=8 -sDEVICE=tiffg4 -o file.tiff tmp.pdf')
            #os.system('convert -density 300 "'+nombre_archivo+'" -depth 8 -strip -background white -alpha off file.tiff')
            os.system("tesseract file.tiff ocr -l spa")
            ocr_txt = io.open("ocr.txt", "r", encoding="utf-8")
            contenido = ocr_txt.read()
            contenido = " ".join(contenido.split())
            sql =  "INSERT IGNORE INTO ocr (tipo,archivo,contenido) VALUES ( '3' , %s , %s )"
            insertar(sql, nombre_archivo, contenido)
            os.system("rm -f file.tiff && rm -f ocr.txt && rm -f tmp.pdf && find /tmp -maxdepth 1 -type f -name 'magick-*' -delete")
            #raw_input("Press Enter to continue...")

def procesar_words(diff):

    for nombre_archivo in diff:
        # cuidado al imprimir, con nohup tira error por bad encoding. Derecho sin nohup no tira error :O
        print "-> "+nombre_archivo
        #arch = subprocess.check_output("php extraertxt_de_docs.php?"+nombre_archivo, shell=True);
        # subprocess.check_output(["... no funca, porque es python < 2.7 :(

        contenidoDOC = Popen(['php', 'extraertxt_de_docs.php', nombre_archivo], stdout=PIPE)
        sql =  '''INSERT IGNORE INTO ocr (tipo,archivo,contenido) VALUES ( '3' , %s , %s )'''
        insertar(sql, nombre_archivo, contenidoDOC.communicate()[0])


try: 
    # Y LUEGO REVEER los que se guardaron vacios-> WHERE LENGTH(contenido)='0'

    ###################### DIGESTO (.DOC*)  #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='3'AND (nombre LIKE '%.doc' OR nombre LIKE '%.docx') "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/intranet/repo/digesto','*.doc*',sql)

    print "---------------archivos de DIGESTO que faltan procesar  *.DOC* -----------------:"

    procesar_words(diff)

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    ###################### DIGESTO (.PDF*)  #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='3'AND nombre LIKE '%.pdf' "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/intranet/repo/digesto','*.pdf',sql)

    print "---------------archivos de DIGESTO que faltan procesar  *.PDF -----------------:"

    procesar_pdf(diff)

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    ###################### DOC CONSEJO (.DOC*) #######################

    sql = " SELECT archivo FROM ocr WHERE tipo='4'AND (nombre LIKE '%.doc' OR nombre LIKE '%.docx') "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/intranet/repo/documentos','*.doc*',sql)

    print "---------------archivos de DOC CONSEJO que faltan procesar *.DOC* -----------------:"

    procesar_words(diff)

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    ###################### DOC CONSEJO (.PDF) #######################

    sql = " SELECT archivo,id FROM ocr WHERE tipo='4'AND nombre LIKE '%.pdf' "

    diff, countinDB, countinFS = lista_diferencia_DBFS('/var/www/intranet/repo/documentos','*.pdf',sql)

    print "---------------archivos de DOC CONSEJO que faltan procesar *.PDF -----------------:"

    procesar_pdf(diff)

    print "en FS:"+str(countinFS)
    print "en DB:"+str(countinDB)

    # Actualizar y rellenar otros campos:

    sql = " SELECT archivo,id FROM ocr WHERE fecha IS NULL "
    insertar("UPDATE ocr SET nombre=SUBSTRING_INDEX(archivo,'/',-1)", "", "")

    for t in getData(sql):
        d = modification_date(t[0])
        print "id: "+str(t[1])+" ->"+d
        insertar("UPDATE ocr SET fecha='"+d+"' WHERE id='"+str(t[1])+"'", "", "")

except:
    print "Error inesperado, eliminando posibles temporales..."
    os.system("rm -f file.tiff && rm -f ocr.txt && rm -f tmp.pdf") # && find /tmp -maxdepth 1 -type f -name 'magick-*' -delete")    
    raise
