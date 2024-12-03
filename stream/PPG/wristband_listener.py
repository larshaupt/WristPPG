import asyncio
import threading
from multiprocessing import Manager, Process
import multiprocessing
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import pyshark
from bleak import BleakClient, BleakScanner
import bleak
from collections import deque
import csv
import os
import numpy as np
import nest_asyncio
nest_asyncio.apply()
import pandas as pd

bracelet_uuids = {
    "S": "F7:67:C7:32:71:21",
    "M": "D1:68:04:87:19:79",
    "L": "D0:90:BD:73:32:48",
    "K": "D6:F7:BD:02:A8:91"    # kapput
}

class DataBuffer:
    def __init__(self, n_channels=19, frame_rate=128, plotting_window=5, csv_window=2, fileindex=0):
        
        # timestamp = time.strftime("%Y%m%d-%H%M%S")
        # self.filename = f"..//recordings//ppg_data_{timestamp}"
        self.filename = f'C://Users//lhauptmann//Code//WristPPG2//data//ppg_{fileindex:03d}'

        self.plotting_winoow = plotting_window
        self.csv_window = csv_window
        self.frame_rate = frame_rate

        self.buffers = [deque(maxlen=int((plotting_window+1)*frame_rate + 1)) for _ in range(n_channels)]
        self.csv_buffers = [deque(maxlen=int((csv_window+1)*frame_rate+1)) for _ in range(n_channels)]

        self.recording = False
        self.n_channels = n_channels
        
        self.running = True

    def add_data(self, qidx, qu):
        # if qu.qsize() > 1:
        while not qu.empty():
            val = qu.get(True, 0.0005)
            self.buffers[qidx].append(val)
            self.csv_buffers[qidx].append(val)
        
    def set_running(self, value):
        self.running = value

    def dump_to_txt(self):
        # with open(self.filename, mode='a', newline='') as file:
        #     writer = csv.writer(file)
        #     for i in range(self.n_channels):
        #         row = f'{i}' + np.array(self.csv_buffers[i]).astype(str)
        #         writer.writerow(row)
        while self.running:
            if self.recording:
                f = open(f"{self.filename}.txt", "a")
                for i in range(self.n_channels):
                    f.write(f"{i} ")
                    while self.csv_buffers[i]:
                        f.write(f"{self.csv_buffers[i].popleft()} ")
                    f.write(" \n")
                f.close()
            time.sleep(self.csv_window)

    def set_recording(self, value):
        if value and not self.recording:
            self.start_recording()
        if self.recording and not value:
            self.stop_recording()
        # self.recording = value

    # def start_data_dump(self):
    #     dump_thread = threading.Thread(target=self.data_dump)
    #     dump_thread.daemon = True
    #     dump_thread.start()
    #     return dump_thread

    # def data_dump(self):
    #     while True:
    #         if self.recording:
    #             self.dump_to_txt()
    #         time.sleep(self.csv_window)

    def start_recording(self):
        self.recording = True
        ti = time.time()
        with open(f"{self.filename}.txt", 'a') as f:
            f.write(f'start time: {ti} \n')
        f.close()
        print("[PPG]: recording started")

    def stop_recording(self):
        self.recording = False
        tf = time.time()

        with open(f"{self.filename}.txt", 'a') as f:
            f.write(f'end time: {tf} \n')
        f.close()

        print("[PPG]: recording stopped")
        print(f"[PPG]: data saved to {self.filename}.txt")

    def plotting_queues(self):
        return [np.array(self.buffers[i]) for i in range(self.n_channels)]

class WristbandListener:
    def __init__(self, bracelet="M", n_ppg_channels=16, frame_rate=128, window_size=5, 
                 csv_window=2, queue_update_rate=16, fileindex=0):
        self.n_ppg_channels = n_ppg_channels
        self.frame_rate = frame_rate
        self.data_queues = [multiprocessing.Queue(maxsize=int((window_size+2)*frame_rate+1)) 
                            for _ in range(n_ppg_channels+4)]
        self.second_cnt = 0  # the device counts seconds
        self.last_idx = -1  # index of received message, counts 0-255 (to check for dropped packages)
        self.last_reception_time = 0
        self.last_msg_chapter = -1
        self.queue_update_rate = queue_update_rate
        self.keep = []
        self.client = None
        self.threads = []
        # self.ppg_exp_avg = [0 for _ in range(n_ppg_channels)]
        # self.sf = 0.9s
        self.data_buffer = DataBuffer(n_channels=n_ppg_channels+4, frame_rate=frame_rate, 
                                      plotting_window=window_size, csv_window=csv_window, fileindex=fileindex) 
        self.package_time = 0
        self.stop_event = threading.Event()  
        
        self.BRACELET_UUID = bracelet_uuids[bracelet]
        self.STREAM_CHAR_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
        self.UART_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
        #self.WIRESHARK_LOG_FP = r'C:\Users\lhauptmann\Code\WristPPG2\stream\PPG\wristband_config3.pcapng'
        #self.WIRESHARK_LOG_FP = r'C:\Users\lhauptmann\Code\WristPPG2\stream\PPG\Lars_112Hz.pcapng'
        #self.WIRESHARK_LOG_FP = r'C:\Users\lhauptmann\Code\WristPPG2\stream\PPG\Lars_112Hz_allchannels.pcapng'
        self.WIRESHARK_LOG_FP = r'C:\Users\lhauptmann\Code\WristPPG2\stream\PPG\Lars_112Hz_Green_Ir.pcapng'
        #self.WIRESHARK_LOG_FP = r'C:\Users\lhauptmann\Code\WristPPG2\stream\PPG\Lars_112Hz_Green_ambient.pcapng'
        #self.WIRESHARK_LOG_FP = r'C:\Users\lhauptmann\Code\WristPPG2\stream\PPG\Lars_112Hz_Green_red.pcapng'
        assert(os.path.isfile(self.WIRESHARK_LOG_FP))

    async def connect_and_stream(self):
        capture = pyshark.FileCapture(self.WIRESHARK_LOG_FP, use_json=True, include_raw=True)
        config_s, config_e = self._find_config_sequence(capture)
        print(f"[PPG]: Found config, start idx: {config_s} end idx: {config_e}")
        print("[PPG]: starting ble scanning ...")
        disconn_cnt = 0
        while not self.stop_event.is_set():
            if self.client is None or not self.client.is_connected:
                self.client = BleakClient(self.BRACELET_UUID)
                try:
                    await self.client.connect()
                except (bleak.exc.BleakDeviceNotFoundError, bleak.exc.BleakError, AttributeError, TimeoutError) as e:
                    print("[PPG]: BLE connect error, retry ", e)
                    disconn_cnt += 1
                if self.client.is_connected:
                    disconn_cnt = 0
                    print("[PPG]: CONNECTED BLE BRACELET")
                    await self._stream(capture, config_s, config_e)
                    while self.data_queues[0].qsize() < 1000 and not self.stop_event.is_set():
                        await asyncio.sleep(1)
                    print("[PPG]: full queues, exit")
                    await capture.close_async()
                    await self.client.stop_notify(self.STREAM_CHAR_UUID)
                    await self.client.disconnect()
                    break
            if disconn_cnt == 3:
                print("[PPG]: BLE device not found, do a scan and retry")
                scanner = BleakScanner()
                await scanner.start()
                await asyncio.sleep(3)
                await scanner.stop()
            elif disconn_cnt > 3:
                print("[PPG]: BLE device still not found, abort!")
                break
            else:
                await asyncio.sleep(1)
                
            

    def _find_config_sequence(self, capture):
        config_s, config_e = None, None
        for capidx, cap in enumerate(capture):
            if config_s is None:
                if 'btatt' in cap.frame_info.protocols and cap.btatt.has_field('uart_tx'):
                    config_s = capidx
            elif 'btatt' in cap.frame_info.protocols and cap.btatt.opcode == '0x1b':
                config_e = capidx
                break
        assert config_s is not None, "[PPG]: Error: no config found in wireshark file"
        assert config_e is not None, "[PPG]: Error: no end of config found in wireshark file"
        return config_s, config_e

    async def _stream(self, capture, config_s, config_e):
        stream_char = self.client.services.get_characteristic(self.STREAM_CHAR_UUID)
        uart_char = self.client.services.get_characteristic(self.UART_CHAR_UUID)
        capture = pyshark.FileCapture(self.WIRESHARK_LOG_FP, use_json=True, include_raw=True)
        for idx, cap in enumerate(capture):
            if idx < config_s or idx > config_e:
                    continue
            if self.stop_event.is_set():
                break
            if 'btatt' in cap.frame_info.protocols:
                if not cap.btatt.has_field('opcode'):
                    print(idx, " no opcode!!!!")
                    continue
                if cap.btatt.opcode == '0x12':
                    uuid = cap.btatt.handle_tree.uuid128.replace(':', '') if cap.btatt.handle_tree.has_field('uuid128') else cap.btatt.handle_tree.characteristic_uuid128.replace(':', '')
                    if uuid == "6e400001b5a3f393e0a9e50e24dcca9e":
                        await self.client.start_notify(stream_char, self.notif_callback)
                    elif uuid == "6e400002b5a3f393e0a9e50e24dcca9e":
                        await self.client.write_gatt_char(uart_char, bytes.fromhex(cap.btatt_raw.value)[3:], response=True)
                elif cap.btatt.opcode in ['0x13', '0x0a', '0x0b']:
                    pass
                else:
                    print(".", end="")
        while self.data_queues[0].qsize()<128 and not self.stop_event.is_set():            
            await asyncio.sleep(1)
            
        await capture.close_async()
            
            
            

    def notif_callback(self, sender, data):
        num_msg_chapters = self.n_ppg_channels // 4
        #print(data)
        if self.last_idx == -1:
            self.missed_messages = {}
            self.last_idx = data[0]
        elif self.last_idx == 255:
            self.last_idx = 0
            if self.missed_messages:
                print("[PPG]: missed messages:", self.missed_messages)
            self.missed_messages = {}
        else:
            self.last_idx += 1
            
        
        try:
            
            idx = data.pop(0)
            
            if idx > self.last_idx:
                print(data)
            #print(idx)
            while idx > self.last_idx: #Package loss
                #print(self.last_idx, idx)
                self.last_idx += 1
                #print("error, missed message idx {}".format(idx))
                if idx in self.missed_messages.keys():
                    self.missed_messages[idx] = (self.missed_messages[idx][0] + 1, self.missed_messages[idx][1] +  time.time() - self.last_reception_time)
                else:
                    self.missed_messages[idx] = (1, time.time() - self.last_reception_time)
                    
                # Fill up the queues with NaNs if package got lost
                self.last_msg_chapter += 1
                self.last_msg_chapter %= num_msg_chapters
                for qu in self.data_queues[self.last_msg_chapter*4:(self.last_msg_chapter+1)*4]:
                    qu.put_nowait(np.nan)
                    
                if self.last_msg_chapter == num_msg_chapters - 1:
                    for qu in self.data_queues[(self.last_msg_chapter+1)*4:(self.last_msg_chapter+1)*4+3]:
                        qu.put_nowait(np.nan)     
                        
                if self.last_msg_chapter == 0: # timestamp
                    self.data_queues[num_msg_chapters*4 + 3].put_nowait(np.nan) 
                

            self.last_reception_time = time.time()
            msg_chapter = data.pop(0)
            self.last_msg_chapter = msg_chapter
            #print(idx, msg_chapter)
            
            
            
            if msg_chapter == 0: # first msg_chapter
                self.data_queues[num_msg_chapters*4 + 3].put_nowait(time.time()) 
                # self.of_flags[:4] = [data[i*4] == 15 for i in range(4)]
                of_flags = [data[i*4] == 15 for i in range(4)]
                ds = [int.from_bytes(data[i*4+1:4+i*4], "big") for i in range(4)]
                for i, (d, qu) in enumerate(zip(ds, self.data_queues[:4])):
                    if of_flags[i]:
                        qu.put_nowait(np.nan)
                    else:
                        qu.put_nowait(d)
                        
                self.keep = data[16:]

            elif msg_chapter in range(1, num_msg_chapters):
                
                new_data = self.keep + data
                of_flags = [new_data[i*4] == 15 for i in range(4)]
                ds = [int.from_bytes(new_data[i*4+1:(i+1)*4], "big") for i in range(4)]
                for i, (d, qu) in enumerate(zip(ds, self.data_queues[4*msg_chapter:4*(msg_chapter+1)])):
                    if of_flags[i]:
                        qu.put_nowait('NaN')
                    else:
                        qu.put_nowait(d)
                self.keep = new_data[16:]

                if msg_chapter == num_msg_chapters - 1: # last msg_chapter
                    ds = [int.from_bytes(self.keep[i*2:(i+1)*2], "big") for i in range(3)]
                    #print(ds)
                    #print(ds, num_msg_chapters*4, num_msg_chapters*4+3, len(self.data_queues))
                    for d, qu in zip(ds, self.data_queues[(msg_chapter+1)*4:(msg_chapter+1)*4+3]):
                        if d > 32768:
                            d -= 65536
                        qu.put_nowait(d / 32768.0 * 8 * 9.8)
                        #print(msg_chapter, (num_msg_chapters+1)*4, (num_msg_chapters+1)*4+3)

            elif msg_chapter == 19: # every second a timestamp
                self.second_cnt += 1
                self.keep = []
                #print("timestamp seconds: ", self.second_cnt)
            else:
                print("chpt ", msg_chapter)
                
        except Exception as exc:
            print("full q")
            print(exc)

    def start_streaming(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.connect_and_stream())

    def start_threads(self):
        if self.threads == []:
            self.threads.append(threading.Thread(target=self.start_streaming, daemon=True))
            self.threads.append(threading.Thread(target=self.data_transfer, daemon=True))
            self.threads.append(threading.Thread(target=self.data_buffer.dump_to_txt, daemon=True))

        for thread in self.threads:
            thread.start()

    def data_transfer(self):
        while not self.stop_event.is_set():
            if self.data_queues[0].empty():
                continue
            for qidx, qu in enumerate(self.data_queues):
                self.data_buffer.add_data(qidx, qu) 
            time.sleep(1.0 / self.queue_update_rate)

    def stop_threads(self):
        
        # Stop recording and join threads
        self.data_buffer.set_recording(False)
        self.stop_event.set()
        for thread in self.threads:
            self.data_buffer.set_running(False)
            #print(thread)
            thread.join()
        self.threads = []
        print("[PPG]: Threads stopped")
        
if __name__ == '__main__':
    listener = WristbandListener(n_ppg_channels=32, frame_rate=128)

    listener.start_threads()
    
    # listener.data_buffer.start_data_dump()
    # asyncio.run(listener.connect_and_stream())
