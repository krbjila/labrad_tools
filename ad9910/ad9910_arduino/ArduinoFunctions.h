#ifndef ArduinoFunctions_h
#define ArduinoFunctions_h

/*
 * Define functions for communicating with Python
 */

#include "Arduino.h"
#include "Constants.h"
#include "String.h"

#define TIMEOUT 1000
#define NUM_PROFILES 8 // Number of profiles, note that profile 0 is reserved for program
#define MAX_LINES 12 // Number of lines to allocate
#define TX_LENGTH 10 // Transmission length 8 bytes

bool T_DONE = false; // Set to true when the transmission is finished
int C_FLAG = 1; // Set to true when the transmission is finished

// DDS program to execute
line** program;

// DDS profiles to set
profile** profiles;

byte** bytesFromPython;

void initProgram(void);
void initProfiles(void);
void zeroProfiles(void);
int readLineFromPython(void);

void disableLines(void);
int findEnabledLines(void);
int serialPrintProgram(int index);
int serialPrintProfile(int index);
void echoData(int lastLine);


// Allocate the program pointer
void initProgram(void) {
  // Allocate the program
  program = (line**)malloc(MAX_LINES * sizeof(line*));
  for (int i=0; i < MAX_LINES; i++) {
    program[i] = (line*)malloc(sizeof(line));
    initLine(program[i]);
  }
}

// Allocate the profiles pointer
void initProfiles(void) {
  // Allocate profiles
  profiles = (profile**)malloc(NUM_PROFILES * sizeof(profile*));
  for (int i=0; i < NUM_PROFILES; i++) {
    profiles[i] = (profile*)malloc(sizeof(profile));
    initProfile(profiles[i]);
    profiles[i]->channel = i;
  }
}

void zeroProfiles(void) {
  byte* ptr;
  for (int i=0; i < NUM_PROFILES; i++) {
    ptr = profiles[i]->dataArray;
    for (int j=0; j < 2 * FTW_LENGTH; j++) {
      *(ptr + j) = zero_reg[j];
    }
  }
}

/*  Reads and processes a line from the Serial port
    If the line is "cxn?" then close the handshake by replying "ad9910\n"
      Return -1
    If the line is "Done" then do nothing -- this is the end of the transmission
      Return -2
    If line is not "Done", then the data should be actual DDS data
      Return "index" after loading the data into the global array bytesFromPython[index]
    If no data, return -3
*/
int readLineFromSerial(void) {
  int lines_read = 0;
 
  if (Serial.available() > 0) { 
    // Read a line:
    String str = Serial.readStringUntil('\n');

    // Due to bug in readStringUntil,
    // you can sometimes read a null string
    // If this happens, just need to read another string in
    if (str.length() == 0)
      str = Serial.readStringUntil('\n');

    if (str.equals("cxn?")) {
      Serial.print("ad9910\n");
      return -1;
    }
    else if (str.equals("Done")) {
        return -2;
    }
    else {
      // Convert String to char*
      // because String is an Arduino object that doesn't work with strtol 
      int str_len = str.length() + 1;
      char temp_char[str_len];
      str.toCharArray(temp_char, str_len);

      // initialize
      const char sep = ',';
      char* token;      

      // Use strtok to separate string on ','
      token = strtok(temp_char, &sep);
      // Get hex byte
      byte temp_byte = byte(strtol(token, NULL, 16));
      // First byte of the line is the line number
      short index = temp_byte;
      // Second byte is the data type
      token = strtok(NULL, &sep);
      temp_byte = byte(strtol(token, NULL, 16));
      short type = temp_byte;

      byte* ptr;
      int readLength;
      if (index < 12) {
        program[index]->enabled = true;
        switch (type) {
          case 0:
            ptr = program[index]->single;
            program[index]->mode = 0;
            readLength = AMPL_LENGTH + POW_LENGTH + FTW_LENGTH;
            break;
          case 1:
            ptr = program[index]->drLimits;
            program[index]->mode = 1;
            readLength = 2 * FTW_LENGTH;
            break;
          case 2:
            ptr = program[index]->drStepSize;
            program[index]->mode = 1;
            readLength = 2 * FTW_LENGTH;
            break;
          case 3:
            ptr = program[index]->drRate;
            program[index]->mode = 1;
            readLength = 2 * RAMP_RATE_LENGTH;
            break;
          case 4:
            bool invert = false;
            token = strtok(NULL, &sep);
            if (token != NULL) {
              temp_byte = byte(strtol(token, NULL, 16));

              if (temp_byte == 1)
                invert = true;
              else
                invert = false;
            }
            program[index]->sweepInvert = invert;
            readLength = 0;
        }
      }
      else {
        short profileIndex = index - 12;
        ptr = profiles[profileIndex]->dataArray;
        readLength = AMPL_LENGTH + POW_LENGTH + FTW_LENGTH;
      }

      int i = 0;
      token = strtok(NULL, &sep);
      while (token!=NULL) {
        temp_byte = byte(strtol(token, NULL, 16));
        if (i < readLength)
          *(ptr + i) = temp_byte;
        token = strtok(NULL, &sep);
        i++;
      }
      return index;
    }
 }
  else
    return -4;
}

void disableLines(void) {
  for (int i=0; i < MAX_LINES; i++) {
    program[i]->enabled = false;
  }
}

// Assume enabled lines appear contiguously
// Returns index of last line enabled
int findEnabledLines(void) {
  int i = 0;
  for (int i=0; i < MAX_LINES; i++) {
    if (!(program[i]->enabled))
      return i - 1;
  }
  return 12;
}


void echoData(int lastLine) {
  for (int i=0; i <= lastLine; i++) {
    serialPrintProgram(i);
  }
  for (int i=0; i < NUM_PROFILES; i++) {
    serialPrintProfile(i);
  }
}


int serialPrintProgram(int index) {
  if (index >= 12) {
    return -1;
  }
  line* ptr = program[index];

  Serial.print(index);
  Serial.print(',');
  Serial.print(ptr->mode, HEX);
  Serial.print(',');
  if (ptr->sweepInvert)
    Serial.print(1);
  else
    Serial.print(0);
  Serial.print(',');
  Serial.print('\n');

  if (ptr->mode == 0) {
    for (int i=0; i < AMPL_LENGTH + POW_LENGTH + FTW_LENGTH; i++) {
      Serial.print(ptr->single[i], HEX);
      Serial.print(",");
    }
    Serial.print("\n");
  }
  else if (ptr->mode == 1) {
    for (int i=0; i < 2 * FTW_LENGTH; i++) {
      Serial.print(ptr->drLimits[i], HEX);
      Serial.print(",");
    }
    Serial.print("\n");
    
    for (int i=0; i < 2 * FTW_LENGTH; i++) {
      Serial.print(ptr->drStepSize[i], HEX);
      Serial.print(",");
    }
    Serial.print("\n");
    
    for (int i=0; i < 2 * RAMP_RATE_LENGTH; i++) {
      Serial.print(ptr->drRate[i],HEX);
      Serial.print(",");
    }
    Serial.print("\n");
  }
}


int serialPrintProfile(int index) {
  if (index >= 8) {
    return -1;
  }
  profile* ptr = profiles[index];

  Serial.print(index,HEX);
  Serial.print(',');
  Serial.print('\n');
  
  for (int i=0; i < 2 * FTW_LENGTH; i++) {
    Serial.print(ptr->dataArray[i],HEX);
    Serial.print(",");
  }
  Serial.print("\n");
}

#endif
