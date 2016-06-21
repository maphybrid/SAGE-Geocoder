#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      atangema
#
# Created:     12/06/2014
# Copyright:   (c) atangema 2014
# Licence:     <your licence>
#-------------------------------------------------------------------------------


from geopy.geocoders import GeocoderDotUS


address, (latitude, longitude) = geolocator.geocode("11111 Euclid Ave unit 13, cleveland, oh")
print(address)