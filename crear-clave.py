from analisis import evaluar
from openpyxl import Workbook
from openpyxl import load_workbook
import os


must_repeat = True

#interfaz
while must_repeat:
    print('introduzca nombre del archivo de claves, sin la extension jpg')
    nombre = input()
    try_name_1 = 'examenes/' + nombre + '.jpg'
    try_name_2 = nombre + '.jpg'
    
    if os.path.exists(try_name_1):
        pre_name = 'examenes/'
    elif os.path.exists(try_name_2): 
        pre_name = ''
    else:
        print('Ningun archivo encontrado llamado ', try_name_2)
        continue
    
   
    print('Archivo ', try_name_2, ' encontrado, ¿Continuar?')
    resp = input()
    if len(resp)>0:
        resp = resp[0].lower()
    else:
        resp = 's'
    if resp in 'sy':
        print('Analizando clave')
        must_repeat = False
    else:
        print('cancelado por usuario, probar nombre nuevo')
        
    print()
    
if not os.path.isdir('examenes_coloreados'):
    os.makedirs('examenes_coloreados')


nombre =pre_name + nombre + '.jpg'

clave = evaluar(nombre)
#Crear workbook nuevo
wb = Workbook()

#Seleccionar la worksheet activa
ws = wb.active

#Guardar los resultados
for line in clave:    
    ws.append(line)
wb.save('clave.xlsx')
del(ws)
del(wb)
print('\n\nAnálisis de clave completado.\n\n')
