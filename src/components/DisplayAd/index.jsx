import React, { useEffect } from 'react'
import { adsense } from "../../../blog-config"

const DisplayAds = () => {
  useEffect(() => {
    const pushAd = () => {
      try {
        const adsbygoogle = window.adsbygoogle
        adsbygoogle.push({})
      } catch (e) {
        console.error(e)
      }
    }

    let interval = setInterval(() => {
      // Check if Adsense script is loaded every 300ms
      if (window.adsbygoogle) {
        pushAd()
        // clear the interval once the ad is pushed so that function isn't called indefinitely
        clearInterval(interval)
      }
    }, 300)

    return () => {
      clearInterval(interval)
    }
  }, [])
  return (
    <>
      {adsense && (
        <ins className="adsbygoogle"
             style={{display: 'block'}}
             data-ad-client={adsense.client}
             data-ad-slot={adsense.slot}
             data-ad-format="auto"
             data-full-width-responsive="true"></ins>
      )}
    </>
  );
}

export default DisplayAds
