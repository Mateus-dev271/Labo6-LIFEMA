#define D1 5
#define D2 4
#define D5 14
#define D6 12
#define D7 13


// ============================================================
// PINES
// ============================================================

int stp = D2;   // STEP
int dir = D1;   // DIR
int ms1 = D5;
int ms2 = D6;
int enb = D7;   // ENABLE


// ============================================================
// PARAMETROS FISICOS
// ============================================================

// Motor de 1.8 grados por paso completo
const float ANGULO_PASO = 1.8;

// Microstepping VALIDADO experimentalmente:
// TMC2209 configurado a 1/16.
const float M = 16.0;

// Correa GT2: 2 mm entre dientes
const float PASO_CORREA = 2.0;

// Polea de 20 dientes
const float DIENTES_POLEA = 20.0;


// ============================================================
// PARAMETROS DE MOVIMIENTO
// ============================================================

// Carrera inicial
float carrera = 450.0;       // [mm]

// Velocidad maxima
float velocidad = 50.0;      // [mm/s]


// ------------------------------------------------------------
// NUEVO:
// aceleracion y desaceleracion
// ------------------------------------------------------------
//
// Estos son los UNICOS parametros nuevos respecto de la
// version que acabamos de validar.
//
// Significan:
//
// aceleracion = 500 mm/s²
//
// La velocidad puede aumentar 500 mm/s cada segundo.
//
// Por ahora NO los modificamos por Serial.
// Primero queremos validar la rampa.
//

float aceleracion = 400.0;      // [mm/s²]
float desaceleracion = 400.0;   // [mm/s²]


// ============================================================
// VARIABLES CALCULADAS
// ============================================================

float pasosCompletosVuelta = 0.0;

float micropasosVuelta = 0.0;

float mmPorVuelta = 0.0;

float micropasosPorMM = 0.0;

float mmPorMicropaso = 0.0;


// Cantidad total de micropasos de la carrera
long int umbralSup = 0;


// Medio periodo de la señal STEP.
// AHORA este valor cambia durante el movimiento.
unsigned long MedioPeriodo = 0;

// MedioPeriodo fijo correspondiente a la velocidad maxima.
// Se usa SIN RECALCULAR durante la meseta.
unsigned long MedioPeriodoMeseta = 0;

// Limites de la meseta expresados en micropasos.
// Solo se usan cuando el perfil es trapezoidal.
long pasosFinAceleracion = 0;
long pasosInicioFrenado = 0;
bool hayMeseta = false;


// Velocidad instantanea calculada
float velocidadActual = 0.0;


// ============================================================
// MAQUINA DE ESTADOS
// ============================================================

typedef enum {
  yendo = 0,
  volviendo = 1,
  esperando = 2,
  moviendose = 3
} Estado;


Estado miEstado = esperando;


// ============================================================
// CONTADOR DE MICROPASOS
// ============================================================

long int pasosRealizados = 0;


// ============================================================
// PROTOTIPOS
// ============================================================

void calcularParametros();

void actualizarRampa();

void lectura();

void step();

void mover();

void ir();

void volver();

void pararMotor();

void revisarEmergencia();

void ajustarCarrera(float valor);

void ajustarVelocidad(float valor);

void imprimirConfiguracion();




// ============================================================
// SETUP
// ============================================================

void setup() {

  Serial.begin(115200);

  // Se mantiene durante esta etapa de prueba porque vimos
  // que el Monitor Serie tarda en reconectarse despues
  // del Upload.
  delay(5000);


  pinMode(stp, OUTPUT);

  pinMode(dir, OUTPUT);

  pinMode(enb, OUTPUT);

  pinMode(ms1, OUTPUT);

  pinMode(ms2, OUTPUT);


  // ----------------------------------------------------------
  // Driver inicialmente deshabilitado
  // ----------------------------------------------------------

  digitalWrite(enb, HIGH);


  // ----------------------------------------------------------
  // CONFIGURACION VALIDADA DEL TMC2209
  //
  // MS1 = HIGH
  // MS2 = HIGH
  //
  // M = 16
  //
  // NO MODIFICAR.
  // ----------------------------------------------------------

  digitalWrite(ms1, HIGH);

  digitalWrite(ms2, HIGH);


  digitalWrite(stp, LOW);


  calcularParametros();


  Serial.println();

  Serial.println("Sistema listo - RAMPA TRAPEZOIDAL");

  Serial.println();

  Serial.println("Comandos:");

  Serial.println("A      -> ir");

  Serial.println("B      -> volver");

  Serial.println("C100   -> carrera = 100 mm");

  Serial.println("V50    -> velocidad maxima = 50 mm/s");

  Serial.println("I      -> mostrar configuracion");


  imprimirConfiguracion();
}


// ============================================================
// LOOP
// ============================================================

void loop() {

  switch (miEstado) {


    case esperando:

      lectura();

      break;


    case volviendo:

      volver();

      break;


    case yendo:

      ir();

      break;


    case moviendose:

      mover();

      break;


    default:

      Serial.println("Estado no reconocido");

      miEstado = esperando;

      break;
  }
}


// ============================================================
// CALCULO DE LOS PARAMETROS MECANICOS
// ============================================================

void calcularParametros() {

  // ----------------------------------------------------------
  // Pasos completos/vuelta
  //
  // 360 / 1.8 = 200
  // ----------------------------------------------------------

  pasosCompletosVuelta =
      360.0 / ANGULO_PASO;


  // ----------------------------------------------------------
  // Micropasos/vuelta
  //
  // 200 * 16 = 3200
  // ----------------------------------------------------------

  micropasosVuelta =
      pasosCompletosVuelta * M;


  // ----------------------------------------------------------
  // Avance lineal por vuelta
  //
  // 20 dientes * 2 mm = 40 mm
  // ----------------------------------------------------------

  mmPorVuelta =
      DIENTES_POLEA * PASO_CORREA;


  // ----------------------------------------------------------
  // Micropasos/mm
  //
  // 3200 / 40 = 80
  // ----------------------------------------------------------

  micropasosPorMM =
      micropasosVuelta / mmPorVuelta;


  // ----------------------------------------------------------
  // Desplazamiento correspondiente a un micropaso
  //
  // 1 / 80 = 0.0125 mm
  // ----------------------------------------------------------

  mmPorMicropaso =
      1.0 / micropasosPorMM;


  // ----------------------------------------------------------
  // Micropasos correspondientes a la carrera
  // ----------------------------------------------------------

  umbralSup =
      round(carrera * micropasosPorMM);


  // Este MedioPeriodo corresponde solamente a Vmax.
  // Durante el movimiento actualizarRampa()
  // lo ira modificando.

  float frecuenciaMaxima =
      velocidad * micropasosPorMM;


  if (frecuenciaMaxima > 0) {

    MedioPeriodo =
        (unsigned long)(
          500000.0 / frecuenciaMaxima
        );

    // Guardamos una copia fija para la meseta.
    // Durante la meseta este valor NO se vuelve a calcular.
    MedioPeriodoMeseta = MedioPeriodo;
  }


  // ----------------------------------------------------------
  // LIMITES DE LA MESETA
  // ----------------------------------------------------------
  // Estas dos distancias son exactamente las mismas que ya
  // usa el programa para diagnosticar el perfil trapezoidal.

  float distanciaAceleracion =
      velocidad * velocidad /
      (2.0 * aceleracion);

  float distanciaFrenado =
      velocidad * velocidad /
      (2.0 * desaceleracion);


  hayMeseta =
      (distanciaAceleracion + distanciaFrenado <= carrera);


  if (hayMeseta) {

    pasosFinAceleracion =
        round(distanciaAceleracion * micropasosPorMM);

    long pasosFrenado =
        round(distanciaFrenado * micropasosPorMM);

    pasosInicioFrenado =
        umbralSup - pasosFrenado;
  }

  else {

    // En perfil triangular no existe meseta.
    // Se conserva exactamente el uso de actualizarRampa().
    pasosFinAceleracion = 0;
    pasosInicioFrenado = 0;
  }
}


// ============================================================
// RAMPA DE VELOCIDAD
// ============================================================
//
// Esta es la principal modificacion respecto del programa
// que ya validamos.
//
// Para cada micropaso calculamos:
//
// 1. cuanto hemos recorrido;
// 2. cuanto falta;
// 3. que velocidad permite la aceleracion;
// 4. que velocidad permite frenar a tiempo;
// 5. elegimos la menor de esas velocidades y Vmax.
//
// Esto produce automaticamente:
//
//     aceleracion
//         |
//         v
//     velocidad constante
//         |
//         v
//     desaceleracion
//
// Si la carrera es demasiado corta para llegar a Vmax,
// el perfil se vuelve triangular automaticamente.
//

void actualizarRampa() {


  // ----------------------------------------------------------
  // DISTANCIA DESDE EL INICIO
  // ----------------------------------------------------------
  //
  // Utilizamos pasosRealizados + 1 para evitar x = 0
  // en el primer micropaso.
  //
  // Si utilizaramos x = 0:
  //
  //     v = sqrt(2*a*x) = 0
  //
  // y no podriamos calcular el periodo.
  // ----------------------------------------------------------

  float distanciaDesdeInicio =
      (pasosRealizados + 1) * mmPorMicropaso;


  // ----------------------------------------------------------
  // DISTANCIA QUE FALTA
  // ----------------------------------------------------------

  long pasosRestantes =
      umbralSup - pasosRealizados;


  float distanciaRestante =
      pasosRestantes * mmPorMicropaso;


  // ==========================================================
  // VELOCIDAD PERMITIDA POR LA ACELERACION
  // ==========================================================
  //
  // Utilizamos:
  //
  //     v² = 2*a*x
  //
  // por lo tanto:
  //
  //     v = sqrt(2*a*x)
  //

  float velocidadPorAceleracion =
      sqrt(
        2.0 *
        aceleracion *
        distanciaDesdeInicio
      );


  // ==========================================================
  // VELOCIDAD MAXIMA QUE PERMITE FRENAR A TIEMPO
  // ==========================================================
  //
  // Para detenernos exactamente al final:
  //
  //     v² = 2*d*x_restante
  //
  // Entonces:
  //
  //     v = sqrt(2*d*x_restante)
  //

  float velocidadPorFrenado =
      sqrt(
        2.0 *
        desaceleracion *
        distanciaRestante
      );


  // ==========================================================
  // ELECCION DE LA VELOCIDAD ACTUAL
  // ==========================================================
  //
  // Tenemos tres limites:
  //
  // 1. velocidad maxima solicitada;
  //
  // 2. velocidad permitida por la aceleracion;
  //
  // 3. velocidad que todavía nos permite frenar.
  //
  // Elegimos la MENOR.
  //

  velocidadActual = velocidad;


  if (velocidadPorAceleracion < velocidadActual) {

    velocidadActual =
        velocidadPorAceleracion;
  }


  if (velocidadPorFrenado < velocidadActual) {

    velocidadActual =
        velocidadPorFrenado;
  }


  // ==========================================================
  // CONVERSION DE VELOCIDAD A FRECUENCIA STEP
  // ==========================================================
  //
  //     fSTEP =
  //
  //     velocidad [mm/s]
  //
  //            x
  //
  //     micropasos/mm
  //

  float frecuenciaStep =
      velocidadActual * micropasosPorMM;


  // ==========================================================
  // CONVERSION DE FRECUENCIA A MEDIO PERIODO
  // ==========================================================
  //
  // Como step() genera:
  //
  // HIGH -> MedioPeriodo
  //
  // LOW  -> MedioPeriodo
  //
  // el periodo completo es:
  //
  //     T = 2 * MedioPeriodo
  //
  // Por lo tanto:
  //
  //     MedioPeriodo =
  //
  //          500000
  //       --------------
  //            fSTEP
  //

  if (frecuenciaStep > 0) {

    MedioPeriodo =
        (unsigned long)(
          500000.0 /
          frecuenciaStep
        );
  }


  // Seguridad:
  //
  // nunca permitimos que el resultado sea cero.

  if (MedioPeriodo < 1) {

    MedioPeriodo = 1;
  }
}


// ============================================================
// GENERAR UN MICROPASO
// ============================================================
//
// NO CAMBIAMOS esta funcion respecto de nuestra base validada.
//

void step() {

  digitalWrite(stp, HIGH);

  delayMicroseconds(MedioPeriodo);

  digitalWrite(stp, LOW);

  delayMicroseconds(MedioPeriodo);
}


// ============================================================
// BOTON DE PANICO
// ============================================================

void revisarEmergencia() {

  while (Serial.available() > 0 ) {

    char dato = Serial.read();

    if (dato == 'x' || dato == 'X') {
      pararMotor();
      Serial.println("Frenado de emergencia");
    }
  }
}


// ============================================================
// LECTURA SERIAL
// ============================================================

void lectura() {

  while (Serial.available() > 0) {

    char dato = Serial.read();


    switch (dato) {


      case 'a':
      case 'A':

        miEstado = yendo;

        break;


      case 'b':
      case 'B':

        miEstado = volviendo;

        break;


      case 'c':
      case 'C':

        ajustarCarrera(
          Serial.parseFloat()
        );

        break;


      case 'v':
      case 'V':

        ajustarVelocidad(
          Serial.parseFloat()
        );

        break;


      case 'i':
      case 'I':

        imprimirConfiguracion();

        break;
    }
  }
}


// ============================================================
// INICIAR IDA
// ============================================================

void ir() {

  digitalWrite(dir, HIGH);

  digitalWrite(enb, LOW);


  // Cada movimiento comienza desde cero.

  pasosRealizados = 0;

  velocidadActual = 0.0;


  miEstado = moviendose;


  Serial.println("motor yendo");
}


// ============================================================
// INICIAR VUELTA
// ============================================================

void volver() {

  digitalWrite(dir, LOW);

  digitalWrite(enb, LOW);


  pasosRealizados = 0;

  velocidadActual = 0.0;


  miEstado = moviendose;


  Serial.println("motor volviendo");
}


// ============================================================
// EJECUTAR MOVIMIENTO
// ============================================================

void mover() {

  revisarEmergencia();

  // ----------------------------------------------------------
  // UNICO CAMBIO FUNCIONAL:
  //
  // Si estamos dentro de una meseta trapezoidal, NO llamamos
  // a actualizarRampa(). MedioPeriodo queda fijo en el valor
  // calculado una sola vez para Vmax.
  //
  // Fuera de la meseta (aceleracion, frenado o perfil
  // triangular) se ejecuta actualizarRampa() exactamente como
  // en el archivo original.
  // ----------------------------------------------------------

  if (
    hayMeseta &&
    pasosRealizados >= pasosFinAceleracion &&
    pasosRealizados < pasosInicioFrenado
  ) {

    MedioPeriodo = MedioPeriodoMeseta;
  }

  else {

    actualizarRampa();
  }


  // ----------------------------------------------------------
  // Desde aqui hasta el final, mover() es igual al original.
  // ----------------------------------------------------------

  step();


  pasosRealizados++;


  // ----------------------------------------------------------
  // Fin de carrera
  // ----------------------------------------------------------

  if (pasosRealizados >= umbralSup) {

    pararMotor();
  }
}


// ============================================================
// DETENER MOTOR
// ============================================================

void pararMotor() {

  miEstado = esperando;


  digitalWrite(enb, HIGH);


  Serial.println("motor apagado");


  Serial.print("Micropasos ejecutados: ");

  Serial.println(pasosRealizados);
}


// ============================================================
// AJUSTAR CARRERA
// ============================================================

void ajustarCarrera(float valor) {

  if (valor <= 0) {

    Serial.println("ERROR: carrera invalida");

    return;
  }


  carrera = valor;


  calcularParametros();


  Serial.print("carrera ajustada a: ");

  Serial.print(carrera);

  Serial.println(" mm");


  Serial.print("micropasos: ");

  Serial.println(umbralSup);
}


// ============================================================
// AJUSTAR VELOCIDAD MAXIMA
// ============================================================

void ajustarVelocidad(float valor) {

  if (valor <= 0) {

    Serial.println("ERROR: velocidad invalida");

    return;
  }


  velocidad = valor;


  calcularParametros();


  Serial.print("velocidad maxima ajustada a: ");

  Serial.print(velocidad);

  Serial.println(" mm/s");
}


// ============================================================
// MOSTRAR CONFIGURACION
// ============================================================

void imprimirConfiguracion() {

  Serial.println();

  Serial.println("====================================");

  Serial.println("CONFIGURACION DEL SISTEMA");

  Serial.println("====================================");


  Serial.print("Microstepping M        : ");

  Serial.println(M);


  Serial.print("Micropasos/vuelta      : ");

  Serial.println(micropasosVuelta);


  Serial.print("mm por vuelta          : ");

  Serial.println(mmPorVuelta);


  Serial.print("Micropasos/mm          : ");

  Serial.println(micropasosPorMM);


  Serial.print("mm por micropaso       : ");

  Serial.println(mmPorMicropaso, 6);


  Serial.print("Carrera                : ");

  Serial.print(carrera);

  Serial.println(" mm");


  Serial.print("Micropasos objetivo    : ");

  Serial.println(umbralSup);


  Serial.print("Velocidad maxima       : ");

  Serial.print(velocidad);

  Serial.println(" mm/s");


  Serial.print("Aceleracion            : ");

  Serial.print(aceleracion);

  Serial.println(" mm/s2");


  Serial.print("Desaceleracion         : ");

  Serial.print(desaceleracion);

  Serial.println(" mm/s2");


  // ----------------------------------------------------------
  // Informacion adicional sobre el perfil
  // ----------------------------------------------------------

  float distanciaAceleracion =
      velocidad * velocidad /
      (2.0 * aceleracion);


  float distanciaFrenado =
      velocidad * velocidad /
      (2.0 * desaceleracion);


  Serial.print("Distancia aceleracion  : ");

  Serial.print(distanciaAceleracion);

  Serial.println(" mm");


  Serial.print("Distancia frenado      : ");

  Serial.print(distanciaFrenado);

  Serial.println(" mm");


  if (
    distanciaAceleracion +
    distanciaFrenado
    <= carrera
  ) {

    Serial.println(
      "Perfil previsto        : TRAPEZOIDAL"
    );

  }

  else {

    Serial.println(
      "Perfil previsto        : TRIANGULAR"
    );
  }


  Serial.println("====================================");
}