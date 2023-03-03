import ipaddress
import asyncio
import subprocess
from tqdm import tqdm


async def ping(ip, sem):
    """
    Asynchronous function that pings an IP address and returns the average latency if the host is alive, or None if the
    host is down.

    :param ip: The IP address to ping.
    :param sem: The semaphore to use for limiting the number of concurrent pings.
    :return: A tuple of the IP address and the average latency, or None if the host is down.
    """
    async with sem:
        # Start the ping process
        p = await asyncio.create_subprocess_exec(
            'ping', '-c', '5', '-i', '0.2', '-W', '1', str(ip),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Wait for the ping process to finish and get the output
        stdout, stderr = await p.communicate()

        # If the ping was successful, extract the average latency from the output and return it along with the IP
        # address. Otherwise, return None.
        if p.returncode == 0:
            # Extract the average latency from the ping output
            output = stdout.decode('utf-8').strip().split('\n')
            rtt_line = output[-1].strip()
            rtt_list = rtt_line.split('=')[-1].split('/')
            avg_latency = float(rtt_list[1])
            return str(ip), avg_latency
        else:
            return None


async def main():
    """
    Asynchronous function that gets an IP subnet from the user, pings each IP address in the subnet, and prints out the
    list of alive hosts along with their average latency.
    """
    # Get the IP subnet from the user
    subnet = input('Enter IP subnet (e.g. 192.168.0.0/24): ')

    # Parse the subnet into an IP network object
    network = ipaddress.ip_network(subnet)

    # Create a semaphore to limit the number of concurrent pings
    sem = asyncio.Semaphore(100)

    # Create a list to hold the ping tasks
    tasks = []

    # Create a progress bar to show the progress of the ping operation
    with tqdm(total=len(list(network.hosts())), desc='Pinging hosts') as pbar:
        # Start a ping task for each IP address in the subnet
        for ip in network.hosts():
            # Create a ping task and add it to the task list
            task = asyncio.create_task(ping(ip, sem))

            # Add a callback to the task that updates the progress bar when the task is done
            task.add_done_callback(lambda x: pbar.update())

            # Add the task to the task list
            tasks.append(task)

        # Wait for all the ping tasks to finish and get the results
        results = await asyncio.gather(*tasks)

    # Filter out the None results (i.e., the hosts that didn't respond to the ping)
    alive = [result for result in results if result is not None]

    # Print out the list of alive hosts along with their average latency
    print('Alive hosts:')
    for ip, latency in alive:
        print(f'{ip} (average latency: {latency:.2f} ms)')

    # Print out a summary of the results
    print(f'Total hosts: {len(list(network.hosts()))}, alive hosts: {len(alive)}')


if __name__ == '__main__':
    asyncio.run(main())
