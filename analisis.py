# import the necessary packages
import numpy as np
import imutils
import cv2
import matplotlib.pyplot as plt

def get_center(points):
    '''
    calcula el punto medio de una nube de puntos 2D.
    También admite arrays de 3 coordenadas, como los obtenidos
    al buscar contornos con opencv
    '''
    if len(points.shape) == 3:
        x_med = np.mean(points[:,0,0])
        y_med = np.mean(points[:,0,1])
        return np.array([x_med, y_med])
    if len(points.shape) == 2:
        x_med = np.mean(points[:,0])
        y_med = np.mean(points[:,1])
        return np.array([x_med, y_med])
    
def get_center_y(points):
    '''
    Calcula la posicion en coordenadas y del centro de una nube de puntos.
    se usa como clave para ordenar las columnas de izquierda a derecha.
    '''
    center = get_center(points)
    return center[0]
    
def get_dist(p1, p2):
    '''
    Calcula la distancia euclidea entre 2 puntos 2D
    '''
    d_x = p1[0]-p2[0]
    d_y = p1[1]-p2[1]
    return np.sqrt(d_x**2 + d_y**2)

def get_submatrix(matrix,rectangle):
    '''
    Recorta de una matriz un rectángulo de forma aproximada a rectangle
    '''
    x_max = np.max(rectangle[:,0,0])
    x_min = np.min(rectangle[:,0,0])
    y_max = np.max(rectangle[:,0,1])
    y_min = np.min(rectangle[:,0,1])
    
    return matrix[y_min:y_max,x_min:x_max].copy()

def get_rect_contour(rectangle):
    '''
    Genera una matriz que contiene los puntos necesarios para
    dibujar un rectangulo orientado circunscrito a los 
    puntos dados.
    '''
    x_max = np.max(rectangle[:,0,0])
    x_min = np.min(rectangle[:,0,0])
    y_max = np.max(rectangle[:,0,1])
    y_min = np.min(rectangle[:,0,1])
    
    rect = np.array([
        [x_max, y_max],
        [x_max, y_min],
        [x_min, y_min],
        [x_min, y_max],
        [x_max, y_max]
    ])
    return rect

def enderezar(mat, direction):
    '''
    Reorienta una matriz dependiendo de la dirección
    '''
    if direction == 0:
        return mat
    if direction == 1:
        return mat.T[:,::-1]
    if direction == 2:
        return mat[::-1,::-1]
    if direction == 3:
        return mat.T[::-1,:]

def get_rectangles(image):
    '''
    Obtiene una lista de los contornos rectangulares 
    ordenados de mayor a menor
    '''
     # find contours in the edge map, then initialize
    # the contour that corresponds to the document
    cnts = cv2.findContours(image.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if imutils.is_cv2() else cnts[1]

    rectangulos = []
    
    # ensure that at least one contour was found
    if len(cnts) > 0:
        # sort the contours according to their size in
        # descending order
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

        # loop over the sorted contours
        for c in cnts:
            # approximate the contour
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)

            # if our approximated contour has four points,
            # then we can assume we have found the paper
            if len(approx) == 4:
                rectangulos.append(approx)
    return rectangulos

def get_orientation(rectangle):
    '''Calcula la orientación vertical u horizontal 
    de un rectángulo dado
    '''

    big_r_p0 = rectangle[0,0,:]
    big_r_p1 = rectangle[1,0,:]
    big_r_p2 = rectangle[2,0,:]

    big_r_l1 = get_dist(big_r_p0, big_r_p1)
    big_r_l2 = get_dist(big_r_p1, big_r_p2)
    big_r_p_far = big_r_p0 if big_r_l1>big_r_l2 else big_r_p2

    big_r_long = np.abs(big_r_p_far - big_r_p1)
    
    if big_r_long[0] > big_r_long[1]:
        orientation, coord = 'hor', 0
    else:
        orientation, coord = 'vert', 1
        
    big_r_long_sign = big_r_p_far - big_r_p1
    angle = np.rad2deg(np.arctan(big_r_long_sign[1-coord]/big_r_long_sign[coord]))
    angle = -angle if orientation == 'hor' else angle
        
    return orientation, coord, angle

def get_direction(image, rectangulos, coord, orientation):
    '''
    Obtiene la direccion del folio a partir de medir 
    a qué lado de las columnas hay mayor cantidad de tinta.
    devuelve la direccion como un int:
        0 = de pie
        1 = girado a la derecha
        2 = girado 180º
        3 = girado a la izquierda
    '''
    min_coord = max(image.shape)
    max_coord = 0
    for ii in range(5):
        element = rectangulos[ii]
        min_coord = min(min_coord, np.min(element[:,0,coord]))    
        max_coord = max(max_coord, np.max(element[:,0,coord]))
    
    #Calculamos la luminosidad de los espacios a ambos lados de las columnas
    corner_space_1 = np.array(image.shape)-1
    corner_space_1[1 - coord] = min_coord
    space_1 = image[:corner_space_1[0], :corner_space_1[1]]

    corner_space_2 = np.array([0,0])
    corner_space_2[1 - coord] = max_coord
    space_2 = image[corner_space_2[0]:, corner_space_2[1]:]

    #El lado más oscuro es la cabecera
    
    if orientation == 'vert':
        if np.mean(space_1) < np.mean(space_2):
            direction = 0
        else:
            direction = 2
    else:
        if np.mean(space_1) < np.mean(space_2):
            direction = 1
        else:
            direction = 3
    return direction

def giro_recorte(image, angle):
    '''
    Gira una imagen y recorta los márgenes necesarios 
    para que no aparezca información espurea en las esquinas.
    '''
    
    if abs(angle)>0.05:        
        rows,cols = image.shape
        M = cv2.getRotationMatrix2D((cols/2,rows/2),-angle,1)
        giro_rect = cv2.warpAffine(image,M,(cols,rows))

        margins = np.ceil(np.array(image.shape)*np.sin(np.deg2rad(abs(angle)))).astype(int)
        giro_margin = giro_rect[margins[0]:-margins[0], margins[1]:-margins[1]]
    else:
        giro_margin = image
    return giro_margin
                
def analizar_casilla(n, casillas):
    '''
    Calcula una fila de datos tras analizar la pregunta
    '''
    #La fila de datos se compodrá del número de la pregunta,
    #la solución propuesta y posibles alertas.
    
    fila = [n+1,]
    sol_casilla = ''
    alerta_casilla = ''
    malas_casillas = ''
    
    #Obtenemos la imagen de la casilla a analizar y la difuminamos
    pregunta_prev = casillas[n]    
    pregunta = cv2.GaussianBlur(pregunta_prev, (35, 35), 0)
    
    #Definimos las secciones de la imagen que analizamos en busca de 
    #trazos escritos
    alto,ancho = pregunta.shape

    alto_cas = round(alto/1.737)
    ancho_cas = round(ancho/7.768)
    y_cas = round(alto/2.543)
    x_cas = round(ancho/3.633)
    ancho_pos = round((ancho - x_cas)/4)
    
    #Guardamos en una lista las imágenes de las casillitas
    #de respuesta que se van a medir
    recuadros = []
    for ii in range(4):
        recuadros.append(pregunta[y_cas:y_cas + alto_cas,x_cas+ ii*ancho_pos: x_cas + ancho_cas+ ii*ancho_pos ])
    
    #Guardamos el valor de la luminosidad media de cada casilla
    medias_cuadros = []
    for ii in range(4):
        medias_cuadros.append(recuadros[ii].mean())

    #Comparamos la luminosidad de cada casilla con la de la
    #casilla más clara de la pregunta.
    #Suponemos que si la diferencia pasa de cierto umbral, es porque 
    #la casilla ha sido oscurecida por trazos escritos.
    
    #Además, supondremos que de todas las casillas con trazos,
    #la más clara es la correcta, ya que para anular se escriben
    #trazos adicionales en la casilla.
    
    num_found = 0 #Número de casillas con trazos 
    found_cell_value = 500 #Guardaremos el valor más claro de casilla con trazos
    found_bad_cell_value = 500 #Esto nos sirve para guardar valores de casillas anuladas
    for ii in enumerate('ABCD'):
        dif = medias_cuadros[ii[0]]-min(medias_cuadros) 
        if dif > 11:
            num_found += 1 #Hemos encontrado una casilla con trazos
            if dif < found_cell_value: #Si es la más clara, es la buena
                found_bad_cell_value = found_cell_value
                found_cell_value = dif
                malas_casillas += sol_casilla
                sol_casilla = ii[1]
            else:
                found_bad_cell_value = min(found_bad_cell_value, dif)
                malas_casillas += ii[1]
        if 11 < dif <= 13 and len(alerta_casilla) == 0: #dejamos un margen de duda
            alerta_casilla += 'cuadros dudosos: ' + ii[1] + ' '
    
    #Añadimos alerta por múltiples respuestas si es necesario         
    if num_found >= 2:
        alerta_casilla += 'varias respuestas detectadas: ' + str(num_found)
    
    #La luminosidad de casillas que consideramos como respuesta
    #se guarda para hacer más análisis después.    
    if num_found >= 1:
        ok_cell_value = found_cell_value        
    else:
        ok_cell_value = max(medias_cuadros)

    fila.append(sol_casilla)
    fila.append(alerta_casilla)    
    fila.append(malas_casillas)
    
    return fila, ok_cell_value
        

def gen_corr_image(image, solucion, rectangulos, root):
    root_divided = root.split('/')
    new_root = 'examenes_coloreados/' + root_divided[-1]
    
    plt.figure(figsize=[20,30])
    plt.imshow(image, cmap=plt.cm.gray)
    letras = {'A':0, 'B':1, 'C':2, 'D':3}
    for n in range(5):
        rectangle = rectangle = get_rect_contour(rectangulos[n])
        plt.plot(rectangle[:,0], rectangle[:,1],'r', lw = 2)
    for n in range(5):
        
        rectangle = rectangulos[n][:,0,:]
        x_max = np.max(rectangle[:,0])
        x_min = np.min(rectangle[:,0])
        y_max = np.max(rectangle[:,1])
        y_min = np.min(rectangle[:,1])
        
        alto = (y_max - y_min)/20
        ancho = x_max - x_min
        
        for ii in range(20):
            jj = n*20 + ii
            y_center = y_min + alto * (ii)
            if len(solucion[jj][2])>0:                
                plt.bar(x_min + ancho/2, alto * 0.7, ancho , y_center, alpha = 0.3, color = 'y')
            if len(solucion[jj][1])>0:
                alto_cas = (alto/1.737)
                ancho_cas = (ancho/7.768)
                y_cas = (alto/2.543)
                x_cas = (ancho/3.633)
                ancho_pos = ((ancho - x_cas)/4)
                
                kk = letras[solucion[jj][1]]
                plt.bar(x_min +x_cas+ kk*ancho_pos + ancho_cas/2 , alto_cas, ancho_cas ,
                        y_center + y_cas, alpha = 0.5, color = 'g')
                
                if len(solucion[jj][3])>0:
                    malas = solucion[jj][3]
                    for mala in malas:
                        kk = letras[mala]
                        plt.bar(x_min +x_cas+ kk*ancho_pos + ancho_cas/2 , alto_cas, ancho_cas ,
                                y_center + y_cas, alpha = 0.5, color = 'r')
    
    plt.axis('off')
    plt.savefig(new_root, bbox_inches = 'tight')
        
def evaluar(root):
    '''
    Calcula la lista de respuestas de una imagen contenida en root.
    También analiza posibles problemas de la lectura.
    '''
    #  Cargamos la imagen desde root:
        
    image = cv2.imread(root)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (11, 11), 0)
    thresh = cv2.threshold(blurred, 0, 255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    #Buscamos contornos rectangulares
    rectangulos = get_rectangles(thresh)
    
    #Calculamos la orientación vertical u horizontal del folio
    orientation, coord, angle = get_orientation(rectangulos[0])           
    
    #Calculamos la orientación exacta del papel
    direction = get_direction(gray, rectangulos, coord, orientation)
     
    #Giramos la imagen para que quedeuna hoja perfectamente vertical
    giro_margin = giro_recorte(blurred, angle)
    papel = enderezar(giro_margin, direction)
    
    #Binarizamos la imagen con un threshold
    thresh = cv2.threshold(papel, 0, 255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    #Obtenemos la posición de las columnas
    rectangulos = get_rectangles(thresh)
    rectangulos = sorted(rectangulos[:5], key=get_center_y, reverse=False)
    
    #Guardamos las columnas en sí en una lista
    columns_gray_ok = []
    for ii in range(5):
        columns_gray_ok.append(get_submatrix(thresh, rectangulos[ii]))
        
    #Columna a columna, guardamos todas las casillas en un lista
    casillas = []
    for n in range(5):
        long = columns_gray_ok[n].shape[0]
        for ii in range(20):
            long_y = (long/20)
            min_y = round(long_y*ii)
            max_y = round(min_y + long_y)
            casillas.append(columns_gray_ok[n][min_y:max_y,:])

    #Analizamos cada casilla a priori           
    solucion = []
    ok_cell_list = []
    
    for n in range(100):        
        fila, ok_cell_value = analizar_casilla(n, casillas)        
        ok_cell_list.append(ok_cell_value)        
        solucion.append(fila)
    
    
    #Con los datos obtenidos, podemos buscar información adicional
    #por ejemplo, buscar posibles respuestas tachadas a partir
    #de casillas tomadas como correctas anormalmente oscuras
        
    ok_cell_max = sorted(ok_cell_list, reverse = True)
    ok_cell_difs = [ok_cell_max[ii] - ok_cell_max[ii+1] for ii in range(7)]

#---- Codigo para debuggear o sacar info adicional ---------  
#    ok_cell_avg = np.mean(ok_cell_list)  
#    for line in solucion:
#        alerta_casilla = line[2]
#        if len(alerta_casilla) > 0:
#            alerta_casilla += '     ok-avg: ' + str(round(ok_cell_avg, 3))
#            alerta_casilla += '     ok-max: ' + str(round(ok_cell_max[0], 3))
#            alerta_casilla += '      difs: '
#            for ii in range(5):
#                dif_cell = ok_cell_difs[ii]
#                alerta_casilla += str(round(dif_cell, 3)) + '  '
#            line[2] = alerta_casilla
#---- Fin del bloque adicional --------------
    max_cell_acc = ok_cell_max[0] + 10
    for ii in enumerate(ok_cell_difs):
        if ii[1] > 7:
            max_cell_acc = ok_cell_max[ii[0]]
    for ii in enumerate(ok_cell_list):
        if ii[1]>= max_cell_acc:
            solucion[ii[0]][2] += 'posible casilla tachada'
    
    gen_corr_image(papel, solucion, rectangulos, root)        
    #Se devuelven todos los datos obtenidos
    return solucion
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
