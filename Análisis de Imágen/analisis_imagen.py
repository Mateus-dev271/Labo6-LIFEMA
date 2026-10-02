import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
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
carpeta = r"C:\Users\mainumbi\Documents\Labo 6-7\juan-mateo\datos\26-09-24\videos\TIFF_binarizado\v_120_51px"
nombre = os.path.basename(carpeta)

# Buscar todos los .tif
archivos = glob.glob(os.path.join(carpeta, "*.tif"))

# Ordenar las imágenes
archivos.sort()

# Cargar todas las imágenes
imagenes = [tifffile.imread(f) for f in archivos]

# Crear el stack
stack = np.stack(imagenes)

print("Dimensiones del stack (nro imag, Xpx, Ypx):", stack.shape)
print("Tipo de datos:", stack.dtype)

#plot de una imagen, puro sanity check
plt.imshow(stack[30], cmap="gray")
plt.title(f"{nombre}")
plt.show()


#%%  #recorte de imagen

#parametros para modificar

margen = 30 #pixeles que dejamos de margen a izq y der al recortar las imagenes
ventana_temporal = 1 #frames que usamos para costruir la imagen representativa 
umbral = 250 # threshold usado luego de calular mean y median


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

for i in range(len(stack)):

    #defino la imagen a recortar
    imagen = stack[i]
    
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

#%%  #calculo de frame inicia y posicion vs t

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

#%%  #frame inicial via std

ventana_std = 20

binarized_stack = stack_recortado > 0
metrica_ventana = np.array([])

for i in range(len(binarized_stack)-ventana_std):
    
    std_map = np.std(binarized_stack[i:i+ventana_std], axis=0)
    
    metrica_ventana = np.append(metrica_ventana , np.sum(std_map))
 
#calculo de frame inicial

porcentaje = 0.95

promedio_estacionario = np.mean(metrica_ventana[int(0.75*len(metrica_ventana)):])
linea_de_corte = (np.max(metrica_ventana) - promedio_estacionario)*(1-porcentaje) + promedio_estacionario

frame_inicial_std = np.where(metrica_ventana <= linea_de_corte)[0][0]


#plots
ejex = np.linspace(0, len(metrica_ventana),len(metrica_ventana))

plt.plot(ejex,metrica_ventana,".", label="std", color="violet")
plt.grid()
plt.legend()


#%%  #costruccion de imagenes representativas 

#imagen promediando 
mean_image = np.mean(stack_recortado[frame_inicial:], axis=0)
representative_mean = (mean_image >= umbral).astype(np.uint8)

#imagen con la mediana
median_image = np.median(stack_recortado[frame_inicial:], axis=0)
representative_median = (median_image >= umbral).astype(np.uint8)

#graficos
fig, axes = plt.subplots(1, 2, figsize=(8, 5), dpi = 150)

axes[0].imshow(representative_mean, cmap='gray', vmin=0, vmax=1)
axes[0].set_title('Mean')
axes[0].axis('off')

axes[1].imshow(representative_median, cmap='gray', vmin=0, vmax=1)
axes[1].set_title('Median')
axes[1].axis('off')

plt.tight_layout()
plt.show()

#%%  #construccion de skeleto via la geodesica

#calculo el punto inicial

left  = np.where(representative_median[0] == 1)[0][0]
right = np.where(representative_median[0] == 1)[0][-1]

x_inicial = int((left + right)*0.5)
y_inicial = 0

#calculo el punto final

#abajo
for j in range(len(representative_median)):

    x1 = np.where(representative_median[-j-1] == 1)[0]
    
    if len(x1) != 0:
        break

x1 = x1[0]
y1 = len(representative_median)-j-1

#arriba
busqueda=[]

for k in range(45):
    
    busqueda.append(np.where(representative_median[y1-k] == 1)[0][0])

x2 = np.min(busqueda)
y2 = y1 - np.argwhere(busqueda==np.min(busqueda))[-1]

#final

x_final = int((x1 + x2)*0.5)
y_final = int((y1 + y2)*0.5)

#calcula distancia al borde
distancias = ndi.distance_transform_edt(representative_median)

#invierte para abaratar el costo del centro
cost_map = distancias.max() - distancias + 0.5

#encarece la parte exterior al filamento
#cost_map[~representative_median] = 999999

#incerto extremos y calculo geodesica
start = (y_inicial, x_inicial)
end = (y_final, x_final)

path, cost = route_through_array(cost_map, start, end, fully_connected=True, geometric=True)

# Convertir el camino a un array para graficarlo
path = np.array(path)


# Crear la figura
fig = plt.figure(figsize=(12, 6), dpi = 150)  # Ancho x Alto

# Definir el layout: 2 filas y 2 columnas
# La columna izquierda ocupará más espacio
gs = gridspec.GridSpec(2, 2,
                       width_ratios=[2, 1],   # Izquierda más ancha (proporción 2:1)
                       height_ratios=[1, 1],  # Las dos de la derecha iguales en altura
                       wspace=0.08,            # Espacio horizontal entre subplots
                       hspace=0.3)            # Espacio vertical entre subplots

# Figura grande a la izquierda (ocupa las dos filas)
ax1 = fig.add_subplot(gs[:, 0])   # Todas las filas, columna 0

ax1.imshow(representative_median, cmap='gray')
ax1.scatter(x_inicial, y_inicial, zorder = 2)
ax1.scatter(x_final, y_final, zorder = 2)
ax1.plot(path[:, 1], path[:, 0], color='red', linewidth=2, label='Eje Central', zorder = 1)
ax1.legend()
ax1.set_title('Median')
ax1.grid()


# Figura superior derecha
ax2 = fig.add_subplot(gs[0, 1])   # Fila 0, columna 1

ax2.imshow(representative_median, cmap='gray')
ax2.scatter(x_inicial, y_inicial, zorder = 2)
ax2.scatter(x_final, y_final, zorder = 2)
ax2.plot(path[:, 1], path[:, 0], color='red', linewidth=2, label='Eje Central', zorder = 1)
ax2.set_xlim(x_inicial -30, x_inicial +30)
ax2.set_ylim(y_inicial +60, y_inicial)
ax2.set_title('Top')
ax2.legend()
ax2.grid()

# Figura inferior derecha
ax3 = fig.add_subplot(gs[1, 1])   # Fila 1, columna 1

ax3.imshow(representative_median, cmap='gray')
ax3.scatter(x_inicial, y_inicial, zorder = 2)
ax3.scatter(x_final, y_final, zorder = 2)
ax3.plot(path[:, 1], path[:, 0], color='red', linewidth=2, label='Eje Central', zorder = 1)
ax3.set_xlim(x_final -20, x_final +40)
ax3.set_ylim(y_final +30, y_final -30)
ax3.set_title('Bottom')
ax3.legend()
ax3.grid()

plt.tight_layout()
plt.show()
