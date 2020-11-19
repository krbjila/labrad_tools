#ifndef Constants_h
#define Constants_h

/*
 * Define AD9910 registers and register depths
 * Define Arduino pins
 * Define "line" and "profile" structs
 */

#include "stdlib.h"

/////////////////////
// I/O Definitions //
/////////////////////
#define SYSCLK 1000 // MHz

/////////////////////////
// AD9910 Register Map //
/////////////////////////
#define CFR1 0x00
#define CFR2 0x01
#define CFR3 0x02
#define AUXDAC 0x03
#define IOUR 0x04
#define FTW 0x07
#define POW 0x08
#define ASF 0x09
#define MSYNC 0x0A
#define DRL 0x0B
#define DRSS 0x0C
#define DRR 0x0D
#define P0 0x0E
#define P1 0x0F
#define P2 0x10
#define P3 0x11
#define P4 0x12
#define P5 0x13
#define P6 0x14
#define P7 0x15
#define RAM 0x16

///////////////////////////////////
// AD9910 Register Depths Lookup //
///////////////////////////////////

const short regDepths[23] {
  // 0x00 to 0x03
  4, 4, 4, 4,
  // 0x04 to 0x07
  4, 0, 0, 4,
  // 0x08 to 0xB
  2, 4, 4, 8,
  // 0x0C to 0x0F
  8, 4, 8, 8,
  // 0x10 to 0x13
  8, 8, 8, 8,
  // 0x14 to 0x16
  8, 8, 4
};

///////////////////////////////////////
// AD9910 Control Register Defaults ///
///////////////////////////////////////
byte cfr1_bytes[4] = {0x00, 0x20, 0x00, 0x00};
byte cfr2_bytes[4] = {0x01, 0x40, 0x00, 0x20};
byte cfr3_bytes[4] = {0x07, 0x00, 0x40, 0x00};
byte auxdac_bytes[4] = {0x00, 0x00, 0x00, 0x7F};

//byte cfr1_bytes[4] = {0x00, 0x00, 0x00, 0x00};
//byte cfr2_bytes[4] = {0x00, 0x40, 0x08, 0x20};
//byte cfr3_bytes[4] = {0x1F, 0x3F, 0x40, 0x00};
//byte auxdac_bytes[4] = {0x00, 0x00, 0x00, 0x7F};

byte cfr2_bytes_drg_enable[4] = {0x00, 0x48, 0x00, 0x20};
byte zero_reg[8] = {0x3F, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};

//////////////////////
// Arduino Port Map //
//////////////////////
#define DRCTL 4
#define DRHOLD 5
#define IO_RESET 6
#define OSK 7
#define IO_UPDATE 11
#define RESET 12
#define TRIG 13

////////////////////////
// Struct definitions //
////////////////////////

#define FTW_LENGTH 4
#define POW_LENGTH 2
#define AMPL_LENGTH 2
#define RAMP_RATE_LENGTH 2


// Struct line for sequence lines
typedef struct line {
  short mode; // 0 for single, 1 for sweep
  bool enabled = false;
  bool sweepInvert = false;
  byte* single; // 8 bytes, {AMPL, POW, FTW} in profile format
  byte* drLimits;
  byte* drStepSize;
  byte* drRate;
} line;

/*
 * Initialize line
 * Returns 0 on success
 */
int initLine(line* ptr) {
  // Check ptr to struct
  if (ptr == NULL) {
    return -1;
  }

  ptr->enabled = false;

  // Allocate struct members
  ptr->single = (byte *)malloc((AMPL_LENGTH + POW_LENGTH + FTW_LENGTH) * sizeof(byte));

  // Check pointers
  if (ptr->single == NULL)
    return -2;
  
  ptr->drLimits = (byte*)malloc(2 * FTW_LENGTH * sizeof(byte));
  ptr->drStepSize = (byte*)malloc(2 * FTW_LENGTH * sizeof(byte));
  ptr->drRate = (byte*)malloc(2 * RAMP_RATE_LENGTH * sizeof(byte));

  // Check pointers
  if (ptr->drLimits == NULL || ptr->drStepSize == NULL || ptr->drRate == NULL)
    return -3;
    
  return 0;
}

/*
 * Free struct members
 * and then the struct
 */
void freeLine(line* ptr, short mode) {
  free(ptr->single);
  free(ptr->drLimits);
  free(ptr->drStepSize);
  free(ptr->drRate);
  free(ptr);
}

// Struct line for sequence lines
typedef struct profile {
  short channel;
  byte* dataArray;
} profile;

/*
 * Initialize profile
 */
int initProfile(profile* ptr) {
  // Check ptr to struct
  if (ptr == NULL) {
    return -1;
  }

  // Allocate struct members
  ptr->dataArray = (byte*)malloc(2 * FTW_LENGTH * sizeof(byte));
  // Check pointers
  if (ptr->dataArray == NULL) {
    return -2;
  }
  else
    return 0;
}

/*
 * Free struct members
 * and then the struct
 */
void freeProfile(profile* ptr) {
  free(ptr->dataArray);
  free(ptr);
}

#endif
