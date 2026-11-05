export function collectionWindow(now=new Date(),years=2){
 const end=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
 const date=new Date(end+'T00:00:00Z');date.setUTCFullYear(date.getUTCFullYear()-years);
 return {start:date.toISOString().slice(0,10),end,years,basis:'manufacturer-release-date; listing-month kept separately'};
}
export function windowCoverage(parts,window=collectionWindow()){
 const counts={confirmedRelease:0,recentListing:0,boundaryListingMonth:0,olderListing:0,dateUnknown:0};
 for(const part of parts.filter(p=>!p.virtual)){
  const release=part.releaseEvidence?.reviewed&&part.releaseEvidence?.sourceUrl&&part.releaseEvidence?.date;
  if(release&&release>=window.start&&release<=window.end)counts.confirmedRelease++;
  const month=part.listingMonth;
  if(!/^\d{4}-\d{2}$/.test(month||''))counts.dateUnknown++;
  else if(month===window.start.slice(0,7))counts.boundaryListingMonth++;
  else if(month>window.start.slice(0,7))counts.recentListing++;
  else counts.olderListing++;
 }
 return {...window,...counts,complete:false};
}
