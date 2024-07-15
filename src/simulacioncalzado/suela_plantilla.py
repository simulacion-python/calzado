import random
import pandas as pd  # type: ignore

"""
Clase para simular el proceso de las plantillas y suelas
"""


class Suela_Plantilla():

    def __init__(self, env, ordenes, tipo, capacidad, df_metricas, df_estado, pipe={}, estado={}):

        self.env = env
        self.df_metricas = df_metricas
        self.df_estado = df_estado
        self.ordenes = ordenes
        self.tipo = tipo
        self.capacidad = capacidad

        self.tiempo_colas = 0
        self.tiempo_proceso = 0

        self.pipe = pipe
        self.estado = estado

    def agregar_simulacion(self):
        _ = [
            self.env.process(self.generador_actividad(orden)) for orden in self.ordenes
            ]

    def generador_actividad(self, orden):

        inicio_tiempo_cola = self.env.now

        if self.estado != {}:
            data_estado = (self.tipo, len(self.capacidad.queue))
            self.estado.put(data_estado)

        with self.capacidad.request() as req:

            yield req
            fin_tiempo_cola = self.env.now

            self.tiempo_colas += (fin_tiempo_cola - inicio_tiempo_cola)
            inicio = self.env.now
            id_actividad = orden["id"]
            cantidad = orden["cantidad"]

            id_producto = 0

            if self.tipo == 2:

                tiempo_actividad = sum(
                    [random.gauss(orden["suela_media"], orden["suela_desv"]) for i in range(cantidad)]
                )

                id_producto = orden["id_suela"]

            elif self.tipo == 3:
                tiempo_actividad = sum(
                    [random.gauss(orden["plantilla_media"], orden["plantilla_desv"]) for i in range(cantidad)]
                )
                id_producto = orden["id_plantilla"]

            yield self.env.timeout(tiempo_actividad)

            if self.estado != {}:
                data_estado = (self.tipo, len(self.capacidad.queue))
                self.estado.put(data_estado)

            fin = self.env.now

            self.tiempo_proceso += (fin-fin_tiempo_cola)

            df_tmp = pd.DataFrame(
                {
                    "tipo": [self.tipo],
                    "id": [id_actividad],
                    "inicio": [inicio],
                    "fin": [fin],
                    "tiempo_proceso": [tiempo_actividad]
                }
            )
            self.df_metricas = self.df_metricas.append(df_tmp)

            if self.pipe != {}:
                data = (self.tipo, id_producto, cantidad, id_actividad)
                self.pipe.put(data)
