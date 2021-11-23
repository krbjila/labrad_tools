#include "string.h"
#include "ArduinoFunctions.h"
#include "DDSFunctions.h"
#include "SPI.h"

int flag = 0;
enum fsm{DATA_INVALID, CXN, DATA_LOAD, ECHO, FORCE_TRIGGERED, PROFILES_LOAD, PROGRAM_RUN, SETUP_NEXT, WAIT_FOR_TRIGGER, TRIGGERED};
enum fsm state = CXN;

int numLines = 0; // Length of the program in modules
int currPos = 0; // Current position in the program
bool forceTriggered = false; // Holds if the program has been force triggered
const long sweepTime = 2000; // length of force triggered sweep


void setup() {
  // Initialize and start serial
  initialize();
  Serial.begin(2400);
  initProgram();
  initProfiles();
}

void loop() {
  // Look for serial data
  // Interrupt sequence if new data is incoming!
  if (Serial.available() > 0) {
    int res = readLineFromSerial();

    if (res == -1) {
      state = CXN;
    }
    else if (res == -2) {
      state = ECHO;
    }
    else if (res == -4) {
      state = FORCE_TRIGGERED;
    }
    else if (res >= 0) {
      state = DATA_LOAD;
    }
    else
      state = DATA_INVALID;
  }
  
  line* current = program[currPos];
  // State machine
  
  switch (state) {
    case DATA_INVALID:
      delay(100);
      break;

    case CXN:
    // connect
      {
        zeroProfiles();
        disableLines();
      }
      break;

    case DATA_LOAD:
    // keep reading
      break;

    case ECHO:
    // read all lines
      {
        int last = findEnabledLines();
        currPos = 0;
        numLines = last + 1;
        echoData(last);
        state = PROFILES_LOAD;
      }
      break;

    case FORCE_TRIGGERED: 
      {
        forceTriggered = true;
        state =  SETUP_NEXT;
      }
      break;

    case PROFILES_LOAD:
    // load profiles onto dds
      {
        ddsCFRInit();
        for (int i = 0; i < NUM_PROFILES; i++) {
          // Write data to profile registers
          // If there was no data from Python for a given register,
          // it should write all zeros (the array is initialized to all zeros)
          byte* data = profiles[i]->dataArray;
          writeRegister(0x0E + i, data, 8);
        }
        // ioUpdate();
        state = SETUP_NEXT;
      }
      break;

   case SETUP_NEXT:
    // Set frequency outputs and sweeps up
    {
      if (current->mode == 1) {
        // set dds to sweep mode drg enable
        // set drLimits, drStepSize, drRate
        writeRegister(DRL, current->drLimits, 8);
        writeRegister(DRSS, current->drStepSize, 8);
        writeRegister(DRR, current->drRate, 4);

        drgEnable(true);

        if (current->sweepInvert) {
          // if inverted, need to let dds sweep up to upper limit
          digitalWrite(DRCTL, HIGH);
        }
        else {
          digitalWrite(DRCTL, LOW);
        }
      }
      else {
        // single frequenct output line
        // set dds to normal mode
        // set profile0 register
        drgEnable(false);
        writeRegister(P0, current->single, 8);
      }
      // update dds
      ioUpdate(); 
      // move to next state
      state = WAIT_FOR_TRIGGER;
  }
    break;

  case WAIT_FOR_TRIGGER:
    {
      // Upon receiving trigger:
    if (digitalRead(TRIG) == HIGH || forceTriggered) {
      // If in sweep mode, need to do something fancy
      if (current->mode == 1) {
        // If sweep is inverted,
        // Just need to change sign of DRCTL
        if (current->sweepInvert) {
          // Pull DRCTL low to execute negative sweep
          digitalWrite(DRCTL, LOW);
        }
        else {
          // Pull DRCTL high to start sweep
          digitalWrite(DRCTL, HIGH);
          }
        }
      state = TRIGGERED;
      }
    else {
      // if no trigger yet, keep waiting
      state = WAIT_FOR_TRIGGER;
      }
    }
    break;

  case TRIGGERED:
    {
      // if still triggered, stay at current line
      if (digitalRead(TRIG) == HIGH) {
        state = TRIGGERED;
      }
      else if (forceTriggered) {
        delay(sweepTime);
        forceTriggered = false;
        state = TRIGGERED;
      }
      else {
        // if last line, go to start
        if (currPos == numLines - 1) {
        currPos = 0;
        }
        // else, advance to next line
        else {
          currPos++;
          }
        state = SETUP_NEXT;
      }
    }  
    break;
  }
}
