import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import tifffile

#%%  #carga de imagens (tiff binarizadas) para analizar

# Carpeta donde están las imágenes
carpeta = r"C:\Users\mainumbi\Documents\Labo 6-7\juan-mateo\datos\26-09-10\videos\TIFF_binarizado\v_50_45px"

# Buscar todos los .tif
archivos = glob.glob(os.path.join(carpeta, "*.tif"))

# Ordenar las imágenes
archivos.sort()

# Cargar todas las imágenes
imagenes = [tifffile.imread(f) for f in archivos]

# Crear el stack
stack = np.stack(imagenes)

print("Dimensiones del stack (nro imag, Ypx, Xpx):", stack.shape)
print("Tipo de datos:", stack.dtype)

#plot de una imagen, puro sanity check
plt.imshow(stack[5], cmap="gray")
plt.show()


#diferencia de velocidades 
X_punta = []
Y_punta = []

stack_long_t = stack #stack con recorte espacial y aca elijo el recorte temporal


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


#%% #plots

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

plt.plot(tiempo_plot[0:100],X_tope[0:100]*scale_mm,"*-", label="X")
plt.grid()
plt.xlabel("s")
plt.ylabel("mm")
plt.title("Tope")
plt.legend()
plt.show()

#%%  #otro calculo de frame inicial

binarized_stack = stack > 0

diff = np.abs(binarized_stack[1:].astype(float)-binarized_stack[:-1].astype(float))
metrica = []

for i in range(len(diff)):
    metrica.append(np.sum(diff[i]))  
    
print(diff)
print(metrica)

ejex_metrica = np.linspace(0, len(metrica),len(metrica))

plt.plot(ejex_metrica,metrica,".")
plt.show()
#%%  #otra forma dos, la venganza

binarized_stack = stack > 0

metrica_ventana = np.array([])

for i in range(len(binarized_stack)-20):
    
    std_map = np.std(binarized_stack[i:i+20], axis=0)
    
    metrica_ventana = np.append(metrica_ventana , np.sum(std_map))
 
ejex = np.linspace(0, len(metrica_ventana),len(metrica_ventana))
#%%
plt.plot(ejex,metrica_ventana,".")
plt.plot(ejex_metrica,metrica,".")

plt.axvline(70)

