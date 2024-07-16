"""
Funciones necesarias para simular el corte y la guarnicion
"""
import simpy
import random
import pandas as pd  # type: ignore
from scipy.stats import norm  # type: ignore

from .hiperparametros import Hiperparametros


class Corte_Guarnicion():
    def __init__(self, env, cortes, df_metricas, df_estado, pipe={}, estado={}):

        # pasar el DF con las metricas
        self.df_metricas = df_metricas
        # Pasar el DF con el estado
        self.df_estado = df_estado
        # Pasar el ambiente de simulacion
        self.env = env

        # Crear el parametro cortadores como un recurso de la simulacion
        # la capacidad se la da la clase estatica Hiperparametros.cantidad_cortadores
        self.cortadores = simpy.Resource(  # type: ignore
            self.env, capacity=Hiperparametros.cantidad_cortadores
        )

        # Crear el parametro guarnecedores como un recurso de la simulacion
        #  la capacidad se la da la clase estatica Hiperparametros.cantidad_gurnecedores
        self.guarnecedores = simpy.Resource(  # type: ignore
            self.env, capacity=Hiperparametros.cantidad_gurnecedores
        )

        # Se parametriza el tiempo en cola como 0 ya que es el paso inicial y no depende
        # de otro proceso
        self.tiempo_colas = 0

        # Se le pasa los datos de los cortes
        self.cortes = cortes

        # para poder tener un cola de espera se realiza un arreglo con ids
        # de cortadores
        self.id_cortadores = [
            id for id in range(Hiperparametros.cantidad_cortadores)
        ]

        # Se define la variable tiempo total inicialmente como 0
        self.tiempo_total = 0
        # Se define la variable tiempo proceso inicialmente como 0
        self.tiempo_proceso = 0

        # Se pasa el objeto pipe para poder conectar los objetos a la
        # simulacion
        self.pipe = pipe

        # Se pasa el estado actual de la simulacion
        self.estado = estado

        # Se define datos como un diccionario vacio
        self.datos = {}

    def get_id_cortador(self):
        """
        Funcion para poder determinar el id del cortador que realizara
        la actividad de corte, retorna el primer elemento del arreglo
        id_cortadores y lo elimina del arreglo
        """
        id = self.id_cortadores[0]
        if len(self.id_cortadores) == 1:
            self.id_cortadores = []
        else:
            self.id_cortadores = self.id_cortadores[1:]
        return id

    def get_laminas(self, area_actual, area_necesaria):
        """
        Funcion que calcula y retorna la cantidad de laminas adicionales
        necesarias para poder ejecutar una orden
        """
        area = area_actual
        laminas_adicionales = 0
        while area < area_necesaria:
            area += random.gauss(
                Hiperparametros.area_media, Hiperparametros.area_desv
            )
            laminas_adicionales += 1
        return laminas_adicionales

    def agregar_simulacion(self):
        """
        Funcion que agrega a los cortadores a la simulacion
        """
        _ = [
            self.env.process(self.generador_cortador(corte))
            for corte in self.cortes
        ]

    def get_tiempo_cambio_cuero(self, id_cortador, cuero, area_media, area_desv):
        """
        Funcion que determina la cantidad de tiempo que necesita el cortador para
        cambiar las laminas de cuero
        """
        tiempo_cambio = 0.0

        if id_cortador not in self.datos:
            self.datos[id_cortador] = {
                "cuero": cuero,
                "area": random.gauss(
                    area_media, area_desv
                )
            }
        if cuero != self.datos[id_cortador]["cuero"]:
            self.datos[id_cortador]["cuero"] = cuero
            self.datos[id_cortador] = {
                "cuero": cuero,
                "area": random.gauss(
                    area_media, area_desv
                )
            }

        tiempo_cambio = random.expovariate(
            1.0 / Hiperparametros.intervalo_cambio_laminas
        )
        return tiempo_cambio

    def generador_cortador(self, corte):
        """
        Funcion que genera el agente cortador para implementar en
        la simulacion
        """
        if self.estado != {}:
            data_corte = (1, len(self.cortadores.queue))
            self.estado.put(data_corte)

        inicio_tiempo_cola = self.env.now

        with self.cortadores.request() as req:
            yield req

        inicio_proceso = self.env.now
        self.tiempo_colas += (inicio_proceso - inicio_tiempo_cola)

        id_cortador = self.get_id_cortador()

        estilo = corte["estilo"]
        cuero = corte["cuero"]
        cantidad = corte["cantidad"]

        area_total = sum(
            [
                random.gauss(
                    corte["area_media"],
                    corte["area_desv"]
                )
                for i in range(cantidad)
            ]
        )

        tiempo_cambio = self.get_tiempo_cambio_cuero(
            id_cortador, cuero, corte["area_media"], corte["area_desv"]
        )

        numero_laminas = self.get_laminas(self.datos[id_cortador]["area"], area_total)

        tiempo_tarea = sum(
            [norm.rvs(size=1, loc=corte["corte_media"], scale=corte["corte_desv"])[0] for i in range(cantidad)]
        )

        tiempo_lamina = sum(
            [
                random.expovariate(1.0 / Hiperparametros.intervalo_cambio_laminas)
                for i in range(numero_laminas)
            ]
        )

        tiempo_total = tiempo_cambio + tiempo_tarea + tiempo_lamina

        yield self.env.timeout(tiempo_total)

        if self.estado != {}:
            data = (1, len(self.cortadores.queue))
            self.estado.put(data)

        self.id_cortadores.append(id_cortador)

        fin_proceso = self.env.now

        self.tiempo_proceso += (fin_proceso - inicio_proceso)

        df_tmp = pd.DataFrame(
            {
                "tipo": [1],
                "id": [corte["id"]],
                "inicio": [inicio_tiempo_cola],
                "fin": [fin_proceso],
                "tiempo_proceso": [tiempo_total]
            }
        )

        df_tmp_estado = pd.DataFrame(
            {
                "fecha": [self.env.now],
                "tipo": [1],
                "cantidad": [1]
            }
        )

        self.df_metricas = self.df_metricas.append(df_tmp)
        self.df_estado = self.df_estado.append(df_tmp_estado)

        g = self.generador_guarnicion(
            corte["guarnicion_media"],
            corte["guarnicion_desv"],
            cantidad,
            estilo,
            corte["id"]
        )
        self.env.process(g)

    def generador_guarnicion(self, media_g, desv_g, cantidad, estilo, id_tarea):

        inicio_tiempo_cola = self.env.now
        with self.guarnecedores.request() as req:

            yield req

        fin_tiempo_cola = self.env.now
        self.tiempo_colas += (fin_tiempo_cola - inicio_tiempo_cola)

        t = sum(
            [
                norm.rvs(
                    size=1,
                    loc=media_g,
                    scale=desv_g
                )[0]
                for i in range(cantidad)
            ]
        )

        yield self.env.timeout(t)

        fin = self.env.now
        self.tiempo_proceso += (fin-fin_tiempo_cola)

        df_tmp = pd.DataFrame(
            {
                "tipo": [4],
                "id": [id_tarea],
                "inicio": [inicio_tiempo_cola],
                "fin": [fin],
                "tiempo_proceso": [t]
            }
        )

        df_tmp_estado = pd.DataFrame(
            {
                "fecha": [self.env.now],
                "tipo": [4],
                "cantidad": [1]
            }
        )

        self.df_metricas = self.df_metricas.append(df_tmp)
        self.df_estado = self.df_estado.append(df_tmp_estado)

        if self.pipe != {}:
            data = (1, estilo, cantidad, id_tarea)
            self.pipe.put(data)
