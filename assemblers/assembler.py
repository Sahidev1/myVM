import argparse
import re
import traceback

INSTRUCTIONS = []
LABELTOPCMAP = {}
PC_START_OFFSET = 0

# R-type op codes
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

#I-type op codes
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

# J-type op codes, we exclude 4 LSb's as they are dont care bits, so we only have 4 MSb's
Jops = {
    'JR':'0110',
    'JALR':'0111',
}

# special operation type that dont fall in line with R, I, J types
specOps = {
    'LUI':'00011100',
    'RSPEC': '10100101',
    'WEPC': '10110101',
}

# supported label instructions
labelOps= {'J', 'JAL', 'BEQL', 'BNEL'}

# supported pseudo instructions
pseudoInstr={
    'NOP':'SLL $0 $0 $0',
    'RPPC':'RSPEC $x 0',
    'REPC':'RSPEC $x 1'
}

# register map
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


# placeholder marker
PLACEHOLDER_PREFIX = '@'

# converts hexadecimals, characters, and integers to integers
def _typeConverter(immStr: str)->int:
    if (re.match(r"^0x[1-9a-f][0-9a-f]{0,3}$", immStr)):
        return int(immStr, 16)
    if (re.match(r"^'\w'$", immStr)):
        return ord(immStr.strip("'"))
    else :
        return int(immStr)

# hack to ensure that the value is 32 bits
def _to_32bit(v: int)->int:
    return v & 0xFFFFFFFF

# parse binary string to integer
def _parseBin(bin: str)->int:
    b = bin.lstrip('0')
    if (b == ''): return 0
    return int(b, 2)

# map register to binary value
def _mapToRegV(reg: str)->int:
    return _parseBin(regMap[reg])

# decompose label instruction and put the decomposed instruction in INSTRUCTIONS array and return updated PC
def _decomposeInstruction(instr: str, currPC: int) -> int:
    instrParts = instr.split()
    if (instrParts[0] in labelOps):
        if (instrParts[0] == 'J' or instrParts[0] == 'JAL'):
            INSTRUCTIONS.append(f'{PLACEHOLDER_PREFIX} LUI $at {instrParts[1]}' )
            INSTRUCTIONS.append(f'{PLACEHOLDER_PREFIX} ORI $at $at {instrParts[1]}')
            if (instrParts[0] == 'JAL'):
                INSTRUCTIONS.append(f'JALR $at $ra')
            else: 
                INSTRUCTIONS.append(f'JR $at')
            return currPC + 3
        if (instrParts[0] == 'BEQL' or instrParts[0] == 'BNEL'):
            INSTRUCTIONS.append(f'{PLACEHOLDER_PREFIX} {instrParts[0][:-1]} {instrParts[1]} {instrParts[2]} {instrParts[3]}')
            return currPC + 1
    else:
        if (re.match(r"^\s*\w+:\s*$", instr)):
            LABELTOPCMAP[instrParts[0][:-1]] = currPC
            return currPC
        else:
            INSTRUCTIONS.append(instr)
            return currPC + 1
# decompose instructions and put them in INSTRUCTIONS array
def _decomposeInstructions(instructions: list) -> None:
    PC = 0
    for instr in instructions:
        PC = _decomposeInstruction(instr.strip() , PC)

# evaluate placeholder and replace it with the actual value in the instruction
def _evaluatePlaceholder(instrPC: int, toReplace: str, replacement: str)->None:
    instr = INSTRUCTIONS[instrPC].split('@')[1].strip()
    INSTRUCTIONS[instrPC] = instr.replace(toReplace, replacement)

# evaluate placeholders in the instructions
def _evaluatePlaceholders()->None:
    for pc in range(len(INSTRUCTIONS)):
        instr = INSTRUCTIONS[pc]
        if(re.match(r"^@.*$",instr)):
            instrParts = instr.split('@')[1].split()
            if (instrParts[0] == 'LUI'):
                jPC = LABELTOPCMAP[instrParts[2]] + PC_START_OFFSET
                _evaluatePlaceholder(pc, instrParts[2], str(jPC>>16))
            elif (instrParts[0] == 'ORI'):
                jPC = LABELTOPCMAP[instrParts[3]] + PC_START_OFFSET
                _evaluatePlaceholder(pc, instrParts[3], str(jPC&0xFFFF))
            else:
                jPC = LABELTOPCMAP[instrParts[3]] + PC_START_OFFSET
                _evaluatePlaceholder(pc, instrParts[3], str(jPC - pc))

# remove instruction at pc
def _remove_instruction(pc: int)->None:
    INSTRUCTIONS.pop(pc)
    for label, pcval in LABELTOPCMAP.items():
        if (pcval > pc):
            LABELTOPCMAP[label] = pcval - 1

# jump optimizer, removes LUI instructions if the label is within 16 bit range
def _jumpOptimizer()->None:
    pc = 0
    while pc < len(INSTRUCTIONS):
        instr = INSTRUCTIONS[pc]
        if(re.match(r"^@.*$",instr)):
            instr = instr.split('@')[1]
            instrParts = instr.split()
            if (instrParts[0] == 'LUI' and LABELTOPCMAP[instrParts[2]]  +  PC_START_OFFSET < int("0xffff",16)):
                _remove_instruction(pc)
                nextParts = INSTRUCTIONS[pc].split()
                INSTRUCTIONS[pc] = f'@ ORI $at $0 {nextParts[4]}'
                continue
        pc += 1

# assemble a non labeled instruction instruction        
def _assembleInstruction(instr: str)->str:
    iPart = instr.split()
    hx = _to_32bit(0)
    if (iPart[0] in Jops):
        hx |= _parseBin(Jops[iPart[0]])
        hx <<= 8
        hx |= _mapToRegV(iPart[1])
        hx <<= 4 
        hx |= 0 if iPart[0] == 'JR' else _mapToRegV(iPart[2])
        hx <<=16
    elif (iPart[0] in Iops):
        hx |= _parseBin(Iops[iPart[0]])
        hx <<= 4
        hx |= _mapToRegV(iPart[1])
        hx <<= 4
        hx |= _mapToRegV(iPart[2])
        hx <<= 16
        hx |= _typeConverter(iPart[3])
    elif(iPart[0] in Rops):
        hx |= _parseBin(Rops[iPart[0]])
        hx <<= 4
        hx |= _mapToRegV(iPart[1])
        hx <<= 4
        hx |= _mapToRegV(iPart[2])
        hx <<= 4
        hx |= _mapToRegV(iPart[3])
        hx <<= 12
    elif(iPart[0] in specOps):
        if (iPart[0] == 'LUI'):
            hx |= _parseBin(specOps[iPart[0]])
            hx <<= 4
            hx |= _mapToRegV(iPart[1])
            hx <<= 20
            hx |= _typeConverter(iPart[2])
        elif (iPart[0] == 'WEPC'):
            hx |= _parseBin(specOps[iPart[0]])
            hx <<= 4
            hx |= _mapToRegV(iPart[1])
            hx <<= 4
            hx |= _mapToRegV('$0')
            hx <<= 16
        elif (iPart[0] == 'RSPEC'):
            hx |= _parseBin(specOps[iPart[0]])
            hx <<= 4
            hx |= _mapToRegV(iPart[1])
            hx <<= 4
            hx |= _mapToRegV('$0')
            hx <<= 16
            hx |= _typeConverter(iPart[2])
    elif(iPart[0] in pseudoInstr):
        if (iPart[0] == 'NOP'):
            hx = _assembleInstruction(pseudoInstr[iPart[0]])
        if (iPart[0] == 'REPC' or iPart[0] == 'RPPC'):
            decInstr = pseudoInstr[iPart[0]].replace('$x', iPart[1])
            return _assembleInstruction(decInstr)
    else :
        print('instruction: ' + instr.split('\n')[0] + ' is invalid instruction')
        exit(1)
    return f'{hx:08x}'

# assemble all instructions
def _assembleInstructions()->None:
    for pc in range(len(INSTRUCTIONS)):
        try :
            INSTRUCTIONS[pc] = _assembleInstruction(INSTRUCTIONS[pc])
        except:
            print(f'Error at instruction: {INSTRUCTIONS[pc]}')
            print(traceback.format_exc())
            exit(1)


# reads a file line by line and returns a list of lines
# ignores blank lines and comments
def _readFileLineByLine(file: str) -> list:
    file = open(file, 'r')
    lines = []
    while True:
        line = file.readline()
        if not line:
            break
        if (re.match(r"^\s*$", line) or re.match(r"^\s*#", line)):
            continue
        lines.append(line)
    file.close()
    return lines




def printInstructions(initMsg: str, mapInst=False)->None:
    pc = 0
    print(initMsg)
    for instr in INSTRUCTIONS:
        if (mapInst):
            print(f'PC: {pc + PC_START_OFFSET}, Machinecode: {instr}, Instruction: {instList[pc]}')
        else:
            print(instr)
        pc += 1

# logisim heximage generator below

args = argparse.ArgumentParser()
args.add_argument('input', help='Input file')
args.add_argument('-m', action='store_true', help='Check for option -m')

args = args.parse_args()

mapInstrToMachineCode = False
instList = []
if args.m:
    mapInstrToMachineCode = True
if args.input:
    lines = _readFileLineByLine(args.input)
    _decomposeInstructions(lines)
    _jumpOptimizer()
    _evaluatePlaceholders()
    if mapInstrToMachineCode:
        instList = list(INSTRUCTIONS)
    _assembleInstructions()

    printInstructions('v2.0 raw', mapInstrToMachineCode)