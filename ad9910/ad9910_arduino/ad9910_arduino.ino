#include "string.h"
#include "ArduinoFunctions.h"
#include "DDSFunctions.h"
#include "SPI.h"

int flag = 0;
enum fsm{DATA_INVALID, CXN, DATA_LOAD, ECHO, PROFILES_LOAD, PROGRAM_RUN};
enum fsm state = CXN;

int numLines = 0; // Length of the program in modules
int currPos = 0; // Current position in the program

int dummy = 0; // GET RID OF ME!

void setup() {
  // Initialize and start serial
  initialize();
  Serial.begin(4800);
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
    else if (res >= 0) {
      state = DATA_LOAD;
    }
    else
      state = DATA_INVALID;
  }

  // State machine
  switch (state) {
    case DATA_INVALID:
      delay(100);
      break;
    case CXN:
      {
        zeroProfiles();
        disableLines();
      }
      break;
    case DATA_LOAD:
      break;
    case ECHO:
      {
        int last = findEnabledLines();
        currPos = 0;
        numLines = last + 1;
        echoData(last);
        state = PROFILES_LOAD;
      }
      break;
    case PROFILES_LOAD:
      {
        ddsCFRInit();
        for (int i = 0; i < NUM_PROFILES; i++) {
          // Write data to profile registers
          // If there was no data from Python for a given register,
          // it should write all zeros (the array is initialized to all zeros)
          byte* data = profiles[i]->dataArray;
          writeRegister(0x0E + i, data, 8);
        }
        ioUpdate();
        state = PROGRAM_RUN;
      }
      break;
    case PROGRAM_RUN:
      {
        // why do i need to do this:
        masterReset();
        ddsCFRInit();

        for (int i = 0; i < NUM_PROFILES; i++) {
          // Write data to profile registers
          // If there was no data from Python for a given register,
          // it should write all zeros (the array is initialized to all zeros)
          byte* data = profiles[i]->dataArray;
          writeRegister(0x0E + i, data, 8);
        }
        
        ioUpdate();
       
        line* current = program[currPos];

        // Set everything up
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
            // digitalWrite(DRHOLD, LOW);
          }
          else {
            digitalWrite(DRCTL, LOW);
            // digitalWrite(DRHOLD, LOW);
          }
        }
        else {
          // set dds to normal mode
          // set profile0 register
          drgEnable(false);
          writeRegister(P0, current->single, 8);
        }

        ioUpdate();

        bool triggered = false;
        bool interrupt = false;
        bool was_triggered = false;

        // Loop while waiting for a trigger
        while (!triggered && !interrupt) {
          // If computer is trying to update
          // Interrupt the while loop
          if (Serial.available() > 0) {
            interrupt = true;
            triggered = false;
            state = CXN;
          }
          // Upon receiving trigger:
          else if (digitalRead(TRIG) == HIGH) {
            triggered = true;

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
          }
        }

        // Once the trigger is received, wait for trigger low
        while (triggered && !interrupt) {
          // If computer is trying to update,
          // interrupt while loop
          if (Serial.available() > 0) {
            interrupt = true;
            triggered = false;
            state = CXN;
          }
          // Otherwise wait for the trigger low
          else if (digitalRead(TRIG) == LOW) {
            triggered = false;

            // If in sweep mode, need to so something fancy
            if (current->mode == 1) {
              // Turn off DRG
              drgEnable(false);
            }
            // Otherwise, just set to all zeros
            else {
              writeRegister(P0, zero_reg, 8);
            }

            // Finally, ioUpdate
            ioUpdate();
            digitalWrite(DRCTL, LOW);
            digitalWrite(DRHOLD, LOW);
            was_triggered = true;
          }
        }

        if (was_triggered) {
          // Finally, update currPos
          if (currPos == numLines - 1) {
            currPos = 0;
          }
          else
            currPos++;
        }
        state = PROGRAM_RUN;
      } 
      break;
  }
//  while (flag == 0) {
//    // put your main code here, to run repeatedly:
//    int res = readLineFromSerial(false);
//    if (res == -1) {
//      digitalWrite(13, LOW);
//      flag = 1;
//    }
//  }
//  while (flag == 1) {
//    int read_status = readLineFromSerial(true);
//    if (read_status >= 0) {
//      byte* arr;
//      arr = bytesFromPython[read_status];
//
//      for (int i=0; i < TX_LENGTH; i++) {
//        Serial.print(arr[i]);
//        Serial.print(',');
//      }
//      Serial.print('\n');
//    }
//    else if (read_status == -2) {
//      Serial.print("Done\n");
//      digitalWrite(13, HIGH);
//      delay(1000);
//      flag = 0;
//    }
//  }
}
