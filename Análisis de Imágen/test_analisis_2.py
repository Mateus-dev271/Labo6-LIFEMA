import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import tifffile
import imageio.v2 as imageio
from skimage.morphology import skeletonize
from skimage.morphology import medial_axis
from skimage.morphology import thin
from scipy import ndimage as ndi
from skimage.graph import route_through_array

#%%  #carga de imagens (tiff binarizadas) para analizar

# Carpeta donde están las imágenes
carpeta = r"C:\Users\mainumbi\Documents\Labo 6-7\juan-mateo\datos\26-09-10\videos\TIFF_binarizado\v_20_45px"

# Buscar todos los .tif
archivos = glob.glob(os.path.join(carpeta, "*.tif"))
nombre = os.path.basename(carpeta)

# Ordenar las imágenes
archivos.sort()

# Cargar todas las imágenes
imagenes = [tifffile.imread(f) for f in archivos]

# Crear el stack
stack = np.stack(imagenes)

print("Dimensiones del stack (nro imag, Xpx, Ypx):", stack.shape)
print("Tipo de datos:", stack.dtype)

#plot de una imagen, puro sanity check
plt.imshow(stack[5], cmap="gray")
plt.title(f"{nombre}")
plt.show()

#%%  #construccion de imagen representativa

#parametros para modificar

margen = 30 #pixeles que dejamos de margen a izq y der al recortar las imagenes
frame_inicial = 0
ventana_temporal = 1 #frames que usamos para costruir la imagen representativa 
umbral = 250 # threshold usado luego de calular mean y median

#%%%

#elijo la imagen estacionaria para definir la region de interes
centro = int(len(stack)*0.75)
plantilla = stack[centro]


#calculo limite derecho
lim_der = np.where(plantilla[0] == 255)[0][-1]

#calculo limite izquierdo
for j in range(len(plantilla)):

    lim_izq = np.where(plantilla[-j-1] == 255)[0]
    
    if len(lim_izq) != 0:
        break

lim_izq = lim_izq[0]

#prints
roi =  lim_der - lim_izq

print("lim_izq =",lim_izq)
print("lim_der =",lim_der)
print("roi =",roi)
print("margen =",margen)

#itero para todas las imagenes
stack_recortado = []

for i in range(len(stack) - frame_inicial):

    #defino la imagen a recortar
    imagen = stack[i + frame_inicial]
    
    #eligo el limite derecho de la imagen
    limite = np.where(imagen[0] == 255)[0][-1]

    #creo imagen vacia y le pego el frame real
    imagen_vacia = np.zeros([ len(imagen) , roi + margen*2 ])

    #creo imagen vacia y le pego el frame real
    imagen_vacia = np.zeros(( len(imagen) , roi + margen*2 ))

    #recorto la imagen
    if (limite - roi - margen) < 0:
        imagen_recortada = imagen[: , 0 : limite + margen]
        
    else:
        imagen_recortada = imagen[: , limite - roi - margen : limite + margen]

    #pego el recorte en la imagen vacia
    imagen_vacia[: , -len(imagen_recortada[0]):] = imagen_recortada

    #guardo el recorte
    stack_recortado.append(imagen_vacia)

#tomo los frames que quiero usar
stack_recortado = np.array(stack_recortado[ventana_temporal:-ventana_temporal])

print("Hay stack!")

#%%  #primer criterio para frame inicial

#diferencia de velocidades 
X_punta = []
Y_punta = []

stack_long_t = stack_recortado #stack con recorte espacial y aca elijo el recorte temporal


#punta inferior

for m in range(len(stack_long_t)):
    
    frame = stack_long_t[m]

    for j in range(len(frame)):

        x_punta = np.where(frame[-j-1] == 255)[0]
    
        if len(x_punta) != 0:
            break

    x_punta = x_punta[0]
    y_punta = len(frame)-j-1
    
    X_punta.append(x_punta)
    Y_punta.append(y_punta)
    
    
#tope superior

X_tope = []

for s in range(len(stack_long_t)):
    
    frame = stack_long_t[s]
    
    x_tope = np.where(frame[0] == 255)[0][-1]
    X_tope.append(x_tope)

X_tope = np.array(X_tope)
X_punta = np.array(X_punta)
Y_punta = np.array(Y_punta)

#calculo del frame inicial
porcentaje = 0.95

promedio_estacionario = np.mean(Y_punta[int(0.75*len(Y_punta)):])
linea_de_corte = (np.max(Y_punta) - promedio_estacionario)*(1-porcentaje) + promedio_estacionario

frame_inicial = np.where(Y_punta <= linea_de_corte)[0][0]


#plots
tiempo_plot = np.linspace(0,len(stack_long_t),len(stack_long_t))

scale_mm = 17.55/45
scale_s = 1/60

fig, ax = plt.subplots(1, 2, figsize=(18, 6), dpi = 150)

ax[0].plot(tiempo_plot, X_punta*scale_mm,"-*", label="X")
ax[0].set_title('X')
ax[0].set_xlabel("s")
ax[0].set_ylabel("mm")
ax[0].grid()
ax[0].legend()

ax[1].plot(tiempo_plot, Y_punta*scale_mm,"-*", label="Y")
ax[1].axhline(linea_de_corte*scale_mm)
ax[1].set_title('Y')
ax[1].set_xlabel("s")
ax[1].set_ylabel("mm")
ax[1].grid()
ax[1].legend()

fig.suptitle("Punta",fontsize=18)
plt.show()




#%%  #cracion de video

# Nombre del archivo de salida
nombre_video = f"video_salida_{nombre}.mp4"

# fps: cuadros por segundo (ajusta la velocidad del video)
fps = 10 

# Guardar el video
with imageio.get_writer(nombre_video, fps=fps, codec='libx264') as writer:
    for img in stack_recortado:
        writer.append_data(img)

print(f"¡Video guardado con éxito como '{nombre_video}'!")

#%%  #segundo y tercer metodo

binarized_stack = stack_recortado > 0

diff = np.abs(binarized_stack[15:].astype(float)-binarized_stack[:-15].astype(float))
metrica = []

for i in range(len(diff)):
    metrica.append(np.sum(diff[i]))  
    
print(diff)
print(metrica)

ejex_metrica = np.linspace(0, len(metrica),len(metrica))

#otro
binarized_stack = stack_recortado > 0

metrica_ventana = np.array([])

for i in range(len(binarized_stack)-20):
    
    std_map = np.std(binarized_stack[i:i+20], axis=0)
    
    metrica_ventana = np.append(metrica_ventana , np.sum(std_map))
 
ejex = np.linspace(0, len(metrica_ventana),len(metrica_ventana))

#plots
plt.plot(ejex,metrica_ventana,".", label="std")
plt.plot(ejex_metrica,metrica,".", label="mean")
plt.grid()
plt.legend()








