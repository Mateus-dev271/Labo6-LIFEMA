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

// Tiempo de transicion de aceleracion en cada empalme.
// 10 ms equivalen aproximadamente a 2 mm a 200 mm/s.
const float tiempoEmpalme = 0.01;  // [s]
const float MICROPASOS_RAMPA_MINIMA = 5.0;


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


// Timer1 usa divisor 16: 5 ticks por microsegundo.
// La cuenta es el periodo entre flancos ascendentes de STEP.
const uint32_t TICKS_POR_US = 5;
const uint32_t PULSO_ALTO_TICKS = 10;  // 2 us
volatile uint32_t periodoPasoTicks = 62500;
volatile bool movimientoTimerActivo = false;
volatile bool pulsoStepAlto = false;
volatile bool movimientoTimerTerminado = false;

// Variables que usa el programa principal para actualizar el perfil.
bool movimientoTimerIniciado = false;
long pasosActualizados = -1;
float fraccionTicksAcumulada = 0.0;

// Indica si la carrera permite meseta considerando los empalmes.
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
// Lo incrementa la interrupcion al completar cada pulso STEP.
volatile long int pasosRealizados = 0;


// ============================================================
// PROTOTIPOS
// ============================================================

void calcularParametros();

void actualizarRampa();

float distanciaEmpalme(float aceleracionLocal);

float aceleracionParaPerfil(float aceleracionLocal);

float velocidadConEmpalme(float distancia, float aceleracionLocal);

void IRAM_ATTR interrupcionTimerPaso();

void iniciarTimerPaso();

void lectura();

void mover();

void ir();

void volver();

void pararMotor();

void ajustarCarrera(float valor);

void ajustarVelocidad(float valor);

void imprimirConfiguracion();

void revisarEmergencia();

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

  // Timer1 queda configurado como temporizador de un solo uso.
  // La interrupcion solo cambia STEP y programa el siguiente flanco.
  timer1_attachInterrupt(interrupcionTimerPaso);
  timer1_enable(TIM_DIV16, TIM_EDGE, TIM_SINGLE);
  timer1_disable();


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


  // Distancias nominales para alcanzar Vmax y empezar a frenar.
  float aceleracionIda = aceleracionParaPerfil(aceleracion);
  float aceleracionVuelta = aceleracionParaPerfil(desaceleracion);

  float distanciaAceleracion =
      velocidad * velocidad /
      (2.0 * aceleracionIda);

  float distanciaFrenado =
      velocidad * velocidad /
      (2.0 * aceleracionVuelta);

  float anchoAceleracion = distanciaEmpalme(aceleracionIda);
  float anchoFrenado = distanciaEmpalme(aceleracionVuelta);

  hayMeseta =
      (distanciaAceleracion + distanciaFrenado
       + 0.5 * anchoAceleracion
       + 0.5 * anchoFrenado <= carrera);
}


// ============================================================
// EMPALMES DE ACELERACION
// ============================================================

float distanciaEmpalme(float aceleracionLocal) {

  aceleracionLocal = aceleracionParaPerfil(aceleracionLocal);

  float distanciaNominal =
      velocidad * velocidad /
      (2.0 * aceleracionLocal);

  float ancho = velocidad * tiempoEmpalme;
  float anchoMinimo = 4.0 * mmPorMicropaso;

  if (ancho < anchoMinimo) {
    ancho = anchoMinimo;
  }

  float anchoMaximo = 0.5 * distanciaNominal;

  if (ancho > anchoMaximo) {
    ancho = anchoMaximo;
  }

  return ancho;
}


// A velocidades muy bajas, la aceleracion nominal llegaria a Vmax
// en menos de un micropaso. Reducimos la aceleracion efectiva para que
// la rampa ocupe al menos cinco micropasos y pueda representarse.
float aceleracionParaPerfil(float aceleracionLocal) {

  if (velocidad <= 0.0 || mmPorMicropaso <= 0.0) {
    return aceleracionLocal;
  }

  float distanciaMinima =
      MICROPASOS_RAMPA_MINIMA * mmPorMicropaso;

  float aceleracionMinimaResoluble =
      velocidad * velocidad / (2.0 * distanciaMinima);

  if (aceleracionLocal > aceleracionMinimaResoluble) {
    return aceleracionMinimaResoluble;
  }

  return aceleracionLocal;
}


// Empalma la envolvente de aceleracion con Vmax mediante una
// curva cubica. La misma funcion, usando distancia restante,
// suaviza el comienzo del frenado.

float velocidadConEmpalme(float distancia, float aceleracionLocal) {

  aceleracionLocal = aceleracionParaPerfil(aceleracionLocal);

  float velocidadRampa =
      sqrt(2.0 * aceleracionLocal * distancia);

  if (!hayMeseta) {
    return velocidadRampa;
  }

  float distanciaNominal =
      velocidad * velocidad /
      (2.0 * aceleracionLocal);

  float ancho = distanciaEmpalme(aceleracionLocal);

  if (ancho <= 0.0) {
    return velocidadRampa;
  }

  float inicio = distanciaNominal - 0.5 * ancho;
  float fin = distanciaNominal + 0.5 * ancho;

  if (distancia <= inicio) {
    return velocidadRampa;
  }

  if (distancia >= fin) {
    return velocidad;
  }

  float velocidadInicio =
      sqrt(2.0 * aceleracionLocal * inicio);

  float pendienteInicio =
      aceleracionLocal / velocidadInicio;

  float s = (distancia - inicio) / ancho;
  float s2 = s * s;
  float s3 = s2 * s;

  float h00 = 2.0 * s3 - 3.0 * s2 + 1.0;
  float h10 = s3 - 2.0 * s2 + s;
  float h01 = -2.0 * s3 + 3.0 * s2;

  return h00 * velocidadInicio
       + h10 * ancho * pendienteInicio
       + h01 * velocidad;
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
      velocidadConEmpalme(
        distanciaDesdeInicio,
        aceleracion
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
      velocidadConEmpalme(
        distanciaRestante,
        desaceleracion
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
  // CONVERSION A PERIODO DE TIMER1
  // ==========================================================

  if (velocidadActual > 0.0) {

    float frecuenciaStep =
        velocidadActual * micropasosPorMM;

    // Timer1 con TIM_DIV16 cuenta a 5 MHz: 5 ticks por us.
    float ticksExactos =
        (1000000.0 / frecuenciaStep) * TICKS_POR_US;

    uint32_t ticks = (uint32_t)ticksExactos;
    fraccionTicksAcumulada += ticksExactos - ticks;

    // Conserva la fraccion sub-tick para no acumular error
    // cuando el periodo no es un numero entero de ticks.
    if (fraccionTicksAcumulada >= 1.0) {
      ticks++;
      fraccionTicksAcumulada -= 1.0;
    }

    if (ticks <= PULSO_ALTO_TICKS) {
      ticks = PULSO_ALTO_TICKS + 1;
    }

    periodoPasoTicks = ticks;
  }
}


// ============================================================
// TIMER1: GENERACION DE LOS FLANCOS STEP
// ============================================================
// La interrupcion no calcula velocidades ni usa Serial.

void IRAM_ATTR interrupcionTimerPaso() {

  if (!movimientoTimerActivo) {
    timer1_disable();
    return;
  }

  if (!pulsoStepAlto) {

    GPIO_REG_WRITE(GPIO_OUT_W1TS_ADDRESS, (1U << stp));
    pulsoStepAlto = true;
    timer1_write(PULSO_ALTO_TICKS);
  }

  else {

    GPIO_REG_WRITE(GPIO_OUT_W1TC_ADDRESS, (1U << stp));
    pulsoStepAlto = false;
    pasosRealizados++;

    if (pasosRealizados >= umbralSup) {
      movimientoTimerActivo = false;
      movimientoTimerTerminado = true;
      timer1_disable();
      return;
    }

    uint32_t periodo = periodoPasoTicks;
    uint32_t ticksBajo = periodo - PULSO_ALTO_TICKS;

    timer1_write(ticksBajo);
  }
}


void iniciarTimerPaso() {

  pulsoStepAlto = false;
  movimientoTimerTerminado = false;
  movimientoTimerActivo = true;

  timer1_enable(TIM_DIV16, TIM_EDGE, TIM_SINGLE);
  timer1_write(1);
}


// ============================================================
// LECTURA SERIAL
// ============================================================

void revisarEmergencia() {

  while (Serial.available() > 0) {

    char dato = Serial.read();

    if (dato == 'x' || dato == 'X') {
      pararMotor();
      Serial.println("motor frenado de emergencia");
    }
  }
}

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
  fraccionTicksAcumulada = 0.0;
  pasosActualizados = -1;
  movimientoTimerIniciado = false;
  movimientoTimerTerminado = false;


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
  fraccionTicksAcumulada = 0.0;
  pasosActualizados = -1;
  movimientoTimerIniciado = false;
  movimientoTimerTerminado = false;


  miEstado = moviendose;


  Serial.println("motor volviendo");
}


// ============================================================
// EJECUTAR MOVIMIENTO
// ============================================================

void mover() {
  revisarEmergencia();

  if (movimientoTimerTerminado) {
    pararMotor();
    return;
  }

  if (!movimientoTimerIniciado) {
    actualizarRampa();
    pasosActualizados = pasosRealizados;
    movimientoTimerIniciado = true;
    iniciarTimerPaso();
    return;
  }

  long pasosAhora = pasosRealizados;

  // Actualiza el perfil una vez por micropaso completado.
  // La interrupcion mantiene STEP temporizado mientras se calcula.
  if (pasosAhora != pasosActualizados && pasosAhora < umbralSup) {
    pasosActualizados = pasosAhora;
    actualizarRampa();
  }
}


// ============================================================
// DETENER MOTOR
// ============================================================

void pararMotor() {

  miEstado = esperando;
  timer1_disable();
  movimientoTimerActivo = false;
  movimientoTimerIniciado = false;
  digitalWrite(stp, LOW);

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

  if (valor < 1.0 || valor > 200.0) {

    Serial.println("ERROR: velocidad debe estar entre 1 y 200 mm/s");

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

  float aceleracionIda = aceleracionParaPerfil(aceleracion);
  float aceleracionVuelta = aceleracionParaPerfil(desaceleracion);

  float distanciaAceleracion =
      velocidad * velocidad /
      (2.0 * aceleracionIda);


  float distanciaFrenado =
      velocidad * velocidad /
      (2.0 * aceleracionVuelta);


  Serial.print("Distancia aceleracion  : ");

  Serial.print(distanciaAceleracion);

  Serial.println(" mm");


  Serial.print("Distancia frenado      : ");

  Serial.print(distanciaFrenado);

  Serial.println(" mm");


  float anchoAceleracion = distanciaEmpalme(aceleracionIda);
  float anchoFrenado = distanciaEmpalme(aceleracionVuelta);

  if (
    distanciaAceleracion +
    distanciaFrenado +
    0.5 * anchoAceleracion +
    0.5 * anchoFrenado
    <= carrera
  ) {

    Serial.println(
      "Perfil previsto        : TRAPEZOIDAL SUAVIZADO"
    );

  }

  else {

    Serial.println(
      "Perfil previsto        : TRIANGULAR (sin meseta)"
    );
  }


  Serial.println("====================================");
}
