'''
    Step One - buffer analysis, and define the relationship as
        Scenario 1. MS: B->B
        Scenario 2. MI
            Scenario 2.1. MI but substitutes PT (MI-S): A->A, A->B, B->A
            Scenario 2.2. MI and complements PT (MI-C): A->C, C->A
        Scenario 3. MC: B->C, C->B, C->C
    Step Two - analyze PT transfers for scenario 1 and 2
        for scenario 1
            If PT transfer >=2, move the trip to scenario 3
            If PT transfer =0 or 1, keep as MS
        for scenario 2.1
            If PT transfer =0: keep as MI-S
            If PT transfer >= 1: move the trip to scenario 2.2 (MI-C)
    Step Three - analyze trip duration for scenario 2
        for scenario 2.1, if the trip takes longer than 6 minutes, move the trip to Scenario 1
        for scenario 2.2, if the trip takes longer than 6 minutes, move the trip to Scenario 3

Note: for NYC metro, route_type <=3 -> route_type!=3

'''

from shapely.geometry import Point
from geopandas import GeoDataFrame
import geopandas as gpd
import pandas as pd
import fiona
import os, csv, numpy

os.chdir(r'...')        ### file directory

d_buffer1 = 0.0037       ### buffer distance (0.0037 degree, 400 meters) - change according to your data
d_buffer2 = 0.000925     ### buffer distance (0.000925 degree, 100 meters) - change according to your data
t_buffer = 600          ### time buffer: 10 min (600s)
t_thed = 12*60          ### time threshold

######################### Read Data #########################
trips=[]            # read bike trips Boston180917
header=[]
firstline = True
with open('XXX.csv','rb') as csvfile:       # bikeshare trip OD data
    f = csv.reader(csvfile)
    for r in f:
        if firstline:
            firstline = False
            header = r
            continue
        trips.append(r)
PTlist=[]          # read PT trips
firstline = True
with open('XXX.csv','rb') as csvfile:       # public transit data
    f = csv.reader(csvfile)
    for r in f:
        if firstline:
            firstline = False
            continue
        if [r[6],r[0]] not in PTlist:
            PTlist.append([r[6],r[0]])    #route_id, stop_id
PTroutes=numpy.asarray(PTlist)

Biketrips = pd.read_csv('XXX.csv')          # bikeshare trip OD data
PTtrips = pd.read_csv('XXX.csv')            # public transit data

######################### Define the function for buffer analysis ########################

def Bike_buffer(OD,d_buffer,a,b,tripid):          
    Bikesub = Biketrips.loc[Biketrips['tripid'] == tripid]             ### may need to change the name of your header
    Bikepoint = Point(zip(Bikesub[OD+'_lon'],Bikesub[OD+'_lat']))      ### may need to change the name of your header
    BikeBuffer=Bikepoint.buffer(d_buffer)
    # extract PT trips in the time buffer: 
    PTsub = PTtrips.loc[PTtrips['departure_time'] <= b]            ### may need to change the name of your header
    PTsub = PTsub.loc[PTsub['departure_time'] >= a]                 ### may need to change the name of your header
    routes = []
    for x,y,r in zip(PTsub['stop_lon'],PTsub['stop_lat'],PTsub['route_id']):             ### may need to change the name of your heade
        if Point(x,y).within(BikeBuffer) and r not in routes:
            routes.append(r)
    if len(routes)==0:
        buf = 0
    else:
        buf = 1
    return buf, routes

######################### Define the function to count public tranasit transfers ########################

def PTtransfer(route1, route2):           
    if len(set(route1).intersection(set(route2)))>0:            # have routes in common -> transfer=0
        trans = 0
    else:
        stop1=[]
        stop2=[]
        for route in route1:                # find all stops of route 1, route 2
            PTsubs = PTroutes[PTroutes[:,0]==route]
            for subroute in PTsubs:
                if subroute[1] not in stop1:
                    stop1.append(subroute[1])
        for route in route2:
            PTsubs = PTroutes[PTroutes[:,0]==route]
            for subroute in PTsubs:
                if subroute[1] not in stop2:
                    stop2.append(subroute[1])
        if len(set(stop1).intersection(set(stop2)))>0:      #route 1 and route 2 have stops in common (have intersections) -> transfer = 1
            trans = 1
        else:
            trans = 2           # transfer >= 2
    return trans

######################### Call functions and write results ########################

with open ('XXX.csv','wb') as csvfile:                  # a new csv file to record the results
    f=csv.writer(csvfile)
    f.writerow(header+['O100','D100','O400','D400','transfer'])

for t in trips:
    #trip ID, O time, D time  
    tripid = int(t[header.index('tripid')])          ### may need to change the name of your header
    Ot = int(t[header.index('starttime')])           ### may need to change the name of your header
    Dt = int(t[header.index('endtime')])             ### may need to change the name of your header
    Oa = Ot-t_buffer            #time buffer for O
    Ob = Ot+t_buffer
    Da = Dt-t_buffer            #time buffer for D
    Db = Dt+t_buffer

    #Buffer Analysis
    O400, O400route = Bike_buffer('O',d_buffer1,Oa,Ob,tripid)       # 400m buffer of Bike O [a,b]
    D400, D400route = Bike_buffer('D',d_buffer1,Da,Db,tripid)       # 400m buffer of Bike D [a,b]
    O100, O100route = Bike_buffer('O',d_buffer2,Oa,Ot,tripid)       # 100m buffer of Bike O [a,t]
    D100, D100route = Bike_buffer('D',d_buffer2,Dt,Db,tripid)       # 100m buffer of Bike D [t,b]

    # PT transfer: call PTtransfer()
    if O100==1 and D100==1:
        trans = PTtransfer(O100route, D100route)
    elif O100==1 and D400==1:
        trans = PTtransfer(O100route, D400route)
    elif D100==1 and O400==1:
        trans = PTtransfer(O400route, D100route)
    elif O400==1 and D400==1:
        trans= PTtransfer(O400route, D400route)
    else:
        trans = 'NA'
    
    # Write (using 'a')
    with open ('XXX.csv','a') as csvfile:           #the csv file created above to record results
        f=csv.writer(csvfile)
        f.writerow(t+[O100,D100,O400,D400,trans])
    print tripid