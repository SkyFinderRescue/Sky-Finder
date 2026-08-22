import assert from'node:assert/strict';
import{freshnessState,formatDistanceImperial,haversineMeters,sanitizeCallsign,shouldPublishPosition}from'../core.mjs';

assert.equal(freshnessState(10000,0,true).label,'LIVE');
assert.equal(freshnessState(30000,1000,true).label,'DELAYED');
assert.equal(freshnessState(90000,1000,false).label,'STALE');
assert.equal(sanitizeCallsign(' Rescue #1!! '),'Rescue 1');
const sb={lat:34.4208,lng:-119.6982};
const nearby={lat:34.4218,lng:-119.6982};
const d=haversineMeters(sb,nearby);
assert.ok(d>100&&d<120);
assert.ok(formatDistanceImperial(d).includes('ft'));
assert.equal(shouldPublishPosition(null,nearby,1000,0),true);
assert.equal(shouldPublishPosition(sb,{...sb,speed:0},5000,1000),false);
assert.equal(shouldPublishPosition(sb,{...sb,speed:0},25000,1000),true);
console.log('Responder prototype core tests: PASS');
