import LabJack

dev = open(T7, ETHERNET)

# GetHandleInfo(dev, DeviceType::Ref{Cint}, ConnectionType::Ref{Cint}, SerialNumber::Ref{Cint}, IPAddress::Ref{Cint}, Port::Ref{Cint}, MaxBytesPerMB::Ref{Cint})
# NamesToAddresses(NumFrames::Cint, aNames::Ref{Cstring}, aAddresses::Ref{Cint}, aTypes::Ref{Cint})
# eStreamStart(dev, ScansPerRead::Integer, NumAddresses::Integer, aScanList::Vector{<:Integer}, ScanRate::Ref{Cdouble})
# eStreamRead(dev, aData::Vector{Cdouble}, DeviceScanBacklog::Ref{Cint}, LJMScanBacklog::Ref{Cint})
# eStreamStop(dev)

addr = Ref{Cint}(0)
type = Ref{Cint}(0)
LJM.NameToAddress("AIN127", addr, type)
display(addr[])

names = ["AIN0", "AIN1", "AIN2"]
addrs = Array{Cint}(undef, length(names))
types = Array{Cint}(undef, length(names))
LJM.NamesToAddresses(Cint(length(names)), Base.cconvert(Ref{Cstring},names), pointer(addrs), pointer(types))
display(addrs)