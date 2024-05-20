import icmplib
import threading
import argparse
import datetime
import time


def perform_request(address, timeout, results):
    """
    Effettua una richiesta all'indirizzo `address` aspettando `timeout` secondi per una risposta.
    Il risultato viene salvato nel dizionario `result` alla chiave `address`.
    """
    try:
        results[address] = icmplib.ping(address, count=1, timeout=timeout, privileged=False)
    except Exception as e:
        results[address] = e.__str__()

def perform_requests(addresses, timeout):
    """
    Effettua una richiesta a ciascun indirizzo in `addresses`, aspettando per ognuno `timeout` secondi.
    Viene atteso un tempo `interval` (intervallo di monitoraggio)>`timeout` per garantire che tutte le richieste siano terminate.
    Restituisce una mappa da indirizzo alla corrispettiva risposta, in un formato variabile a seconda della presenza di errori.
    """
    results = {} # mappa indirizzo:risposta
    threads=[]
    # ogni host viene pingato in un thread separato
    for address in addresses:
        thread=threading.Thread(target=perform_request, args=(address,timeout,results))
        threads.append(thread)
        thread.start()
    # attendo la terminazione di tutti i thread
    for thread in threads:
        thread.join()
    return results

def show_results(results, timestamp) -> None:
    """
    Stampa i risultati `results` del monitoraggio iniziato al tempo `timestamp`.
    """
    print(f"Monitoraggio in orario {datetime.datetime.fromtimestamp(timestamp)}")
    for address,response in sorted(results.items(), key=lambda item : item[0]): # risultati in ordine alfanumerico
        print(f"Host {address}:".ljust(30),"\t", end="")
        if response is None:
            print(f"non disponibile (errore: {response})")
        else:
            if response.is_alive:
                print(f"disponibile (rtt: {response.min_rtt}ms)")
            else:
                print("non disponibile (timeout scaduto)")
    print("-"*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser() # parser degli argomenti a riga di comandi
    parser.add_help = True
    parser.add_argument("-i", "--interval", type=float, action="store", default=2, help="intervallo di tempo tra il termine di un monitoraggio e l'inizio del seguente (secondi)")
    parser.add_argument("-t", "--timeout", type=float, action="store", default=1, help="tempo massimo di attesa per una risposta (secondi)")
    parser.add_argument("-a", "--addresses", nargs="+", required=True, help="indirizzi ip/hostname/FQDN degli host da monitorare")
    args = vars(parser.parse_args()) # mappa parametro:valore
    timeout=args["timeout"]
    addresses=args["addresses"]
    interval=args["interval"]

    # controllo sul timeout e l'intervallo di monitoraggio
    if timeout>interval:
        print("Timeout troppo lungo (deve essere inferiore all'intervallo di monitoraggio)")
        exit(1)
    # controllo che gli indirizzi forniti siano validi ed esistano o che gli hostname siano risolvibili
    for address in addresses:
        if not icmplib.is_hostname(address) and not icmplib.is_ipv4_address(address) and not icmplib.is_ipv6_address(address):
            print(f"L'indirizzo {address} non è valido (deve essere un valido hostname/FQDN, IPv4 o IPv6)")
            exit(1)
        if icmplib.is_hostname(address):
            try:
                icmplib.resolve(address)
            except icmplib.NameLookupError:
                print(f"L'indirizzo {address} non è risolvibile nel corrispondente indirizzo IP")
                exit(1)

    try:
        while True:
            start=time.time()
            responses=perform_requests(addresses, timeout)
            show_results(responses,start)
            end=time.time()
            if end-start<interval:
                time.sleep(interval-(end-start))
    except KeyboardInterrupt:
        print("Monitoraggio di rete terminato con successo!")
