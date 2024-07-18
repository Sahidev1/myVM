import argparse
import re

PC = 0
INSTRUCTIONS = []
LABELMAP = {}
MAXLABELPC = 0
INSERTFLAG = False

Rops = {
    'OR':'00000000',
    'AND':'00000001',
    'XOR': '00000010',
    'NOR': '00000011',
    'NAND': '00000100',
    'ADD': '00000101',
    'SUB': '00000110',
    'SLL': '00000111',
    'SRL': '00001000',
    'SRA': '00001001',
    'SLT': '00001010',
    'XNOR': '00001011',
    'MUL': '00001101',
    'DIV': '00001110',
}

Iops = {
    'ORI':'00010000',
    'ANDI':'00010001',
    'XORI': '00010010',
    'NORI': '00010011',
    'NANDI': '00010100',
    'ADDI': '00010101',
    'SUBI': '00010110',
    'SLLI': '00010111',
    'SRLI': '00011000',
    'SRAI': '00011001',
    'SLTI': '00011010',
    'XNORI': '00011011',
    'MULI': '00011101',
    'DIVI': '00011110',
    'LB': '00100101',
    'SB': '00110101',
    'LW': '01000101',
    'SW': '01010101',
    'BEQ': '10000110',
    'BNE': '10010110',
}

JopsMSB = {
    'JR':'0110',
    'JALR':'0111',
}

LabelOps= {'J', 'JAL'}

regMap = {
    '$0':'0000',
    '$v0': '0001',
    '$v1': '0010',
    '$a0': '0011',
    '$a1': '0100',
    '$a2': '0101',
    '$t0': '0110',
    '$t1': '0111',
    '$at': '1000', # Assembler temporary
    '$s0': '1001',
    '$s1': '1010',
    '$s2': '1011',
    '$gp': '1100',
    '$sp': '1101',
    '$fp': '1110',
    '$ra': '1111',
}



NOP_CODE = 'SLL $0 $0 $0'
LUI_OPCODE = '00011100'


def to_32bit(v):
    return v & 0xFFFFFFFF

def parseBin(bin):
    b = bin.lstrip('0')
    if (b == ''): return 0
    return int(b, 2)

def mapToRegV(reg):
    return parseBin(regMap[reg])


def handleLabelOp(instr):
    iPart = instr.split()
    lv = 0
    if (iPart[0] == 'J'):
        label = iPart[1]
        lv = LABELMAP[label]
        assemble_instruction(f'LUI $at {lv>>16}')
        assemble_instruction(f'ORI $at $at {lv&0xFFFF}')
        assemble_instruction(f'JR $at')
    elif (iPart[0] == 'JAL'):
        label = iPart[1]
        lv = LABELMAP[label]
        assemble_instruction(f'LUI $at {lv>>16}')
        assemble_instruction(f'ORI $at $at {lv&0xFFFF}')
        assemble_instruction(f'JALR $at $ra')
    else :
        print('instruction: ' + instr.split('\n')[0] + ' is invalid instruction')
        exit(1)


def instructionScanner(instr):
    iPart = instr.split()
    if (iPart[0] in LabelOps):
        handleLabelOp(instr)
    else:
        assemble_instruction(instr)

def isLabel(instr):
    return instr.split(':')[0] in LABELMAP

def assemble_instruction(instr):
    iPart = instr.split()
    hx = to_32bit(0)
    if (iPart[0] in JopsMSB):
        hx |= parseBin(JopsMSB[iPart[0]])
        hx = hx<<8
        hx |= mapToRegV(iPart[1])
        hx <<= 4 
        hx |= 0 if iPart[0] == 'JR' else mapToRegV(iPart[2])
        hx = hx<<16
    elif (iPart[0] in Iops):
        hx |= parseBin(Iops[iPart[0]])
        hx <<= 4
        hx |= mapToRegV(iPart[1])
        hx <<= 4
        hx |= mapToRegV(iPart[2])
        hx <<= 16
        hx |= int(iPart[3])
    elif(iPart[0] in Rops):
        hx |= parseBin(Rops[iPart[0]])
        hx <<= 4
        hx |= mapToRegV(iPart[1])
        hx <<= 4
        hx |= mapToRegV(iPart[2])
        hx <<= 4
        hx |= mapToRegV(iPart[3])
        hx <<= 12
    
    elif(iPart[0] == 'LUI'):
        hx |= parseBin(LUI_OPCODE)
        hx <<= 4
        hx |= mapToRegV(iPart[1])
        hx <<= 20
        hx |= int(iPart[2])

    elif(iPart[0] == 'NOP'):
        assemble_instruction(NOP_CODE)
        return
    else :
        print('instruction: ' + instr.split('\n')[0] + ' is invalid instruction')
        exit(1)
    

    hxform = f'{hx:08x}'
    if (INSERTFLAG):
        INSTRUCTIONS.insert(0, hxform)
    else:
        INSTRUCTIONS.append(hxform)
    if (mapAsm):
        print(f'{hxform} : {instr}')
    global PC
    PC += 1


def readLineByLINE(fileName):
    with open(fileName) as f:
        lines = f.readlines()
        return lines
def readAll(fileName):
    with open(fileName) as f:
        lines = f.read()
        return lines
    
def scanLabelInstructions(lines_str):
    matches = re.findall(r'^\w+:\n(?:\s{4}[\w \$]+\n?)+', lines_str, re.MULTILINE)
    for match in matches:
        label = match.split(':')[0]
        instructions = match.split(':')[1].lstrip().rstrip().split('\n')
        LABELMAP[label] = PC
        for instruction in instructions:
            #print('instr: '+instruction)
            instructionScanner(instruction)
    global MAXLABELPC
    MAXLABELPC = PC
    
        
def scanInstructions(lines):
    i = 0    
    while i < len(lines):
        if (isLabel(lines[i])):
            i += 1
            while (i < len(lines) and re.match(r'\s{4}.*', lines[i])):
                i += 1
            continue
        instructionScanner(lines[i])
        i += 1 


args = argparse.ArgumentParser()
args.add_argument('input', help='Input file')
args.add_argument('-m', action='store_true', help='Check for option -m')
# i want args parser to check for option -m, please write the code to do it below

mapAsm = False
args = args.parse_args()
if args.m:
    mapAsm = True
if args.input:
    lines = readLineByLINE(args.input)
    lineStr = readAll(args.input)
    PC += 3
    scanLabelInstructions(lineStr)
    scanInstructions(lines)
    INSERTFLAG = True
    assemble_instruction(f'JR $at')
    assemble_instruction(f'ORI $at $at {MAXLABELPC & 0xFFFF}')
    assemble_instruction(f'LUI $at {MAXLABELPC >> 16}')

    if (not mapAsm):
        print('v2.0 raw')
        for instr in INSTRUCTIONS:
            print(instr)

else :
    print('No input file provided')
    exit(1)

