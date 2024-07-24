# myVM

In this project a virtual machine has been created through hardware virtualization using Logisim, a digital logic simulator software. An assembly language has also been designed for VM.

This repository contains the VM Logisim file as well as an assembler for the VM. 

# VM logisim architecture
The virtual machine so far consists of a CPU and a RAM module. The RAM module is a shared instruction and data memory. 

## CPU
The CPU is a 32bit CPU. 

Below is an overview of the CPU and RAM module. At this point the RAM module and CPU or in a common circuit module.
![CPU overview](readmefiles/CPU.png)

### registers
The CPU consists of 16 32 bit registers. All registers can be read and written to. Which register to  read or write to is determined by the instruction registry decoder. The registry decoder decodes the RD (Destination Register) for writes, and the RS (Source register) and RT(Target register) for reads. 
The read RS and RT register value are output by the registers module. 
### ALU
The CPU consists of one 32bit ALU that can perform basic logic and arithmetic operations. All operations except for multiplication and division is a 32bit operations, the aforementioned operations are only support in 16 bits. 
