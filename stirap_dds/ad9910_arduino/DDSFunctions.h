#ifndef DDSFunctions_h
#define DDSFunctions_h

/*
 * Define functions for programming the DDS
 */

#include "Arduino.h"
#include "SPI.h"
#include "Constants.h" // Arduino port map, DDS register map

///////////////////////////
// Function declarations //
///////////////////////////

// Initialize port, SPI
// Do master reset
// and initialize control registers to defaults
void initialize(void);

// Set SPI settings and initialize SPI port
void spiInit(void);

// Set pin modes and default values on Arduino
void portInit(void);

// Master reset DDS
void masterReset(void);

// Pulse I/O update pin
void ioUpdate(void);

// Write to a DDS register using SPI
int writeRegister(int reg, byte* bytes, int num_bytes);

// Write default values to control registers
int ddsCFRInit(void);

void drgEnable(bool flag);


//////////////////////////
// Function definitions //
//////////////////////////

/*
 * Initialization
 */
void initialize(void) {
  portInit();
  spiInit();
  masterReset();
  ddsCFRInit();
}

/*
 * SPI initialization
 */
void spiInit(void) {
  SPI.setDataMode(MSBFIRST);
  SPI.setDataMode(SPI_MODE0);
  SPI.setClockDivider(SPI_CLOCK_DIV4);
  SPI.begin();
}

/*
 * Arduino initialization
 */
void portInit(void) {
  pinMode(DRCTL, OUTPUT);
  digitalWrite(DRCTL, LOW);
  
  pinMode(DRHOLD, OUTPUT);
  digitalWrite(DRHOLD, LOW);
  
  pinMode(IO_RESET, OUTPUT);
  digitalWrite(IO_RESET, LOW);
  
  pinMode(OSK, OUTPUT);
  digitalWrite(OSK, LOW);
  
  pinMode(IO_UPDATE, OUTPUT);
  digitalWrite(IO_UPDATE, LOW);
  
  pinMode(RESET, OUTPUT);
  digitalWrite(RESET, LOW);

  pinMode(SS, OUTPUT);
  digitalWrite(SS, LOW);
  
  pinMode(TRIG, INPUT);
}

/*
 * Assert master reset pin
 */
void masterReset(void) {
  digitalWrite(RESET, HIGH);
  delayMicroseconds(100);
  digitalWrite(RESET, LOW);
}

/*
 * Do I/O update on DDS
 * Note: this assumes a 1 GHz SYSCLK
 */
void ioUpdate(void) {
  digitalWrite(IO_UPDATE, HIGH);
  delayMicroseconds(50);
  digitalWrite(IO_UPDATE, LOW);
}

/*
 * Do I/O reset on DDS
 */
void ioReset(void) {
  digitalWrite(IO_RESET, HIGH);
  delayMicroseconds(100);
  digitalWrite(IO_UPDATE, LOW);
}

/*
 * Write to a DDS register
 * The byte array should be from most significant byte to least significant
 * Returns 0 on success, -1 if num_bytes is larger than the register depth
 */
int writeRegister(int reg, byte* bytes, int num_bytes) {
  // Lookup register depth
  short regDepth = regDepths[reg];

  // Check for invalid num_bytes
  if (num_bytes > regDepth) {
    return -1; 
  }

  // Pull slave select low
  digitalWrite(SS, LOW);

  SPI.transfer(reg);
  
  // Write the bytes
  for (int i = 0; i < num_bytes; i++) {
    SPI.transfer(*(bytes + i));
  }

  // If wrote less bytes than the length of the register
  // need to do I/O reset
  if (num_bytes < regDepth) {
    ioReset();
  }
  
  // Pull SS high
  digitalWrite(SS, HIGH);
  return 0;
}

/*
 * Initialize the control registers
 * Return 0 on success
 */
int ddsCFRInit(void) {
  int err1 = writeRegister(CFR1, cfr1_bytes, 4);
  if (err1 != 0)
    return -1;
  else
    ioUpdate();
    
  int err2 = writeRegister(CFR2, cfr2_bytes, 4);
  if (err2 != 0)
    return -2;
  else
    ioUpdate();
    
  int err3 = writeRegister(CFR3, cfr3_bytes, 4);
  if (err3 != 0)
    return -3;
  else
    ioUpdate();
    
  int err4 = writeRegister(AUXDAC, auxdac_bytes, 4);
  if (err4 != 0)
    return -4;
  else
    ioUpdate();

  return 0;
}

/*
 * Enable/disable DRG function
 * Input: flag
 *  If true: enable DRG
 *  If false: disable DRG
 */
void drgEnable(bool flag) {
  if (flag)
    // Enable the DRG
    writeRegister(CFR2, cfr2_bytes_drg_enable, 4);
  else // Reset to defaults (no DRG)
    writeRegister(CFR2, cfr2_bytes, 4);
}


#endif
