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
"""
import os
import io
import fnmatch
import mysql.connector
from mysql.connector import errorcode
#import subprocess
from subprocess import PIPE,Popen

def conectarMySQL():
    # Si jode insert sql grandote cambiar max_allowed_packet en my.cnf
    # o ...
    # /opt/lampp/bin/mysql -uroot -p  --max_allowed_packet=1073741824 < insert.sql
    try:
        cnx = mysql.connector.connect(user='<usuario>',
                                      password='<contraseña>',
                                      host='localhost',
                                      database='<DB>',
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

def find_files(directory, patron):
    for root, dirs, files in os.walk(directory):
        for basename in files:
            # IMPORTANTE!!! : decode('windows-1252') porque las rutas estan en
            # utf8 en linux, pero python por defecto esta en ASCII -.-
            if fnmatch.fnmatch(basename.decode('windows-1252'), patron):
                filename = os.path.join(root, basename.decode('windows-1252'))
                yield filename

###################### DIGESTO (.DOC*)  #######################

# Y LUEGO REVEER los que se guardaron vacios-> WHERE LENGTH(contenido)='0'

sql = " SELECT archivo FROM ocr WHERE tipo='3'AND (nombre LIKE '%.doc' OR nombre LIKE '%.docx') "

lista_archivosDB = []
countinDB = 0
for t in getData(sql):  # ->cursor.fetchall
    lista_archivosDB.append(t[0])
    #print t[0]
    countinDB = countinDB + 1
archivos_enFS = []
#print "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n"

countinFS = 0

for nombre_archivo in find_files('/var/www/intranet/repo/digesto', '*.doc*'):
    archivos_enFS.append(nombre_archivo)
    countinFS = countinFS + 1

diff = []
diff = list(set(archivos_enFS) - set(lista_archivosDB))

print "---------------archivos de DIGESTO que faltan procesar  *.DOC* -----------------:"

for nombre_archivo in diff:

    print nombre_archivo
    #arch = subprocess.check_output("php extraertxt_de_docs.php?"+nombre_archivo, shell=True);
    # subprocess.check_output(["... no funca, porque es python < 2.7 :(

    contenidoDOC = Popen(['php', 'extraertxt_de_docs.php', nombre_archivo], stdout=PIPE)
    sql =  '''INSERT IGNORE INTO ocr (tipo,archivo,contenido) VALUES ( '3' , %s , %s )'''
    insertar(sql, nombre_archivo, contenidoDOC.communicate()[0])

print "en FS:"+str(countinFS)
print "en DB:"+str(countinDB)

insertar("UPDATE ocr SET nombre=SUBSTRING_INDEX(archivo,'/',-1)", "", "")
###################### DIGESTO (.PDF*)  #######################

# Y LUEGO REVEER los que se guardaron vacios-> WHERE LENGTH(contenido)='0'

sql = " SELECT archivo FROM ocr WHERE tipo='3'AND nombre LIKE '%.pdf' "

lista_archivosDB = []
countinDB = 0
for t in getData(sql):  # ->cursor.fetchall
    lista_archivosDB.append(t[0])
    #print t[0]
    countinDB = countinDB + 1

archivos_enFS = []
countinFS = 0

for nombre_archivo in find_files('/var/www/intranet/repo/digesto', '*.pdf'):
    archivos_enFS.append(nombre_archivo)
    countinFS = countinFS + 1

diff = []
diff = list(set(archivos_enFS) - set(lista_archivosDB))

print "---------------archivos de DIGESTO que faltan procesar  *.PDF -----------------:"

for nombre_archivo in diff:
    print '->'+nombre_archivo
    os.system('convert -density 300 "'+nombre_archivo+'" -depth 8 -strip -background white -alpha off file.tiff')
    os.system("tesseract file.tiff ocr -l spa")
    ocr_txt = io.open("ocr.txt", "r", encoding="utf-8")
    contenido = ocr_txt.read()
    contenido = " ".join(contenido.split())
    sql =  "INSERT IGNORE INTO ocr (tipo,archivo,contenido) VALUES ( '3' , %s , %s )"
    insertar(sql, nombre_archivo, contenido)
    os.system("rm file.tiff && rm ocr.txt")

print "en FS:"+str(countinFS)
print "en DB:"+str(countinDB)

insertar("UPDATE ocr SET nombre=SUBSTRING_INDEX(archivo,'/',-1)", "", "")

###################### DOC CONSEJO (.DOC*) #######################

sql = " SELECT archivo FROM ocr WHERE tipo='4'AND (nombre LIKE '%.doc' OR nombre LIKE '%.docx') "

lista_archivosDB = []
countinDB = 0
for t in getData(sql):  # ->cursor.fetchall
    lista_archivosDB.append(t[0])
    #print "en db-> "+t[0]
    countinDB = countinDB + 1
archivos_enFS = []

countinFS = 0

for nombre_archivo in find_files('/var/www/intranet/repo/documentos', '*.doc*'):
    archivos_enFS.append(nombre_archivo)
    countinFS = countinFS + 1
    #print "en fs-> "+nombre_archivo

diff = []
diff = list(set(archivos_enFS) - set(lista_archivosDB))

print "---------------archivos de DOC CONSEJO que faltan procesar *.DOC* -----------------:"

for nombre_archivo in diff:

    print nombre_archivo
    contenidoDOC = Popen(['php', 'extraertxt_de_docs.php', nombre_archivo], stdout=PIPE)
    sql =  '''INSERT IGNORE INTO ocr (tipo,archivo,contenido) VALUES ( '4' , %s , %s )'''
    insertar(sql, nombre_archivo, contenidoDOC.communicate()[0])

print "en FS:"+str(countinFS)
print "en DB:"+str(countinDB)

insertar("UPDATE ocr SET nombre=SUBSTRING_INDEX(archivo,'/',-1)", "", "")

###################### DOC CONSEJO (.PDF) #######################

sql = " SELECT archivo FROM ocr WHERE tipo='4'AND nombre LIKE '%.pdf' "

lista_archivosDB = []
countinDB = 0
for t in getData(sql):  # ->cursor.fetchall
    lista_archivosDB.append(t[0])
    #print "en db-> "+t[0]
    countinDB = countinDB + 1
archivos_enFS = []

countinFS = 0

for nombre_archivo in find_files('/var/www/intranet/repo/documentos', '*.pdf'):
    archivos_enFS.append(nombre_archivo)
    countinFS = countinFS + 1
    #print "en fs-> "+nombre_archivo

diff = []
diff = list(set(archivos_enFS) - set(lista_archivosDB))

print "---------------archivos de DOC CONSEJO que faltan procesar *.PDF -----------------:"

for nombre_archivo in diff:
    print '->'+nombre_archivo
    os.system('convert -density 300 "'+nombre_archivo+'" -depth 8 -strip -background white -alpha off file.tiff')
    os.system("tesseract file.tiff ocr -l spa")
    ocr_txt = io.open("ocr.txt", "r", encoding="utf-8")
    contenido = ocr_txt.read()
    contenido = " ".join(contenido.split())
    sql =  "INSERT IGNORE INTO ocr (tipo,archivo,contenido) VALUES ( '4' , %s , %s )"
    insertar(sql, nombre_archivo, contenido)
    os.system("rm file.tiff && rm ocr.txt")


print "en FS:"+str(countinFS)
print "en DB:"+str(countinDB)

insertar("UPDATE ocr SET nombre=SUBSTRING_INDEX(archivo,'/',-1)", "", "")
