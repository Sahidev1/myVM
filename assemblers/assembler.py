import argparse
import re

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


def handleLabelOp(instr, labelMap):
    iPart = instr.split()
    retCode = ''
    if (iPart[0] == 'J'):
        label = iPart[1]
        lv = labelMap[label] + 1
        retCode = assemble_instruction(f'LUI $at {lv>>16}') + '\n'
        retCode += assemble_instruction(f'ORI $at $at {lv&0xFFFF}') + '\n'
        retCode += assemble_instruction(f'JR $at')
    return retCode


def instructionScanner(instr, labelMap):
    iPart = instr.split()
    if (iPart[0] in LabelOps):
        return handleLabelOp(instr, labelMap)
    else:
        return assemble_instruction(instr)



def assemble_instruction(instr):
    iPart = instr.split()
    hx = to_32bit(0)
    if (iPart[0] in JopsMSB):
        hx |= parseBin(JopsMSB[iPart[0]])
        hx = hx<<8
        hx |= mapToRegV(iPart[1])
        hx = hx<<20
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
        return assemble_instruction(NOP_CODE)
    else :
        print('instruction: ' + instr.split('\n')[0] + ' is invalid instruction')
        exit(1)
    

    hxform = f'{hx:08x}'
    return hxform


def readInstructionsFromFile(fileName):
    with open(fileName) as f:
        lines = f.readlines()
        return lines
    

def labelMapper(lines):
    labelMap = {}
    lineNum = 0
    for line in lines:
        lineNum += 1
        if re.match(r"(.+):$", line.strip()):
            labelMap[line.strip()[:-1]] = to_32bit(lineNum)
    return labelMap

args = argparse.ArgumentParser()
args.add_argument('input', help='Input file')

args = args.parse_args()
if args.input:
    lines = readInstructionsFromFile(args.input)
    labelMap = labelMapper(lines)
    print('v2.0 raw')
    for line in lines:
        if line.strip()[:-1] in labelMap:
            continue
        print(instructionScanner(line, labelMap))
else :
    print('No input file provided')
    exit(1)

