import rentoLogo from '../../assets/image/rento_logo.png'
import mapImage from '../../assets/image/map.png'
import tiltBg from '../../assets/image/tilt.png'
import streetEasyLogo from '../../assets/image/StreetEasy_logo.png'
import craigslistLogo from '../../assets/image/Craglist_logo.png'

interface Props {
  onGetStarted: () => void
}

export function Hero({ onGetStarted }: Props) {
  return (
    <section
      style={{
        position: 'relative',
        background: '#F6F6F7',
        minHeight: '56vh',
        overflow: 'hidden',
      }}
    >
      {/* Texture overlay */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `url(${tiltBg})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          opacity: 0.55,
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      {/* Map — absolute right */}
      <div
        style={{
          position: 'absolute',
          right: 0,
          top: 0,
          bottom: 0,
          width: '52%',
          overflow: 'hidden',
          zIndex: 1,
          pointerEvents: 'none',
        }}
      >
        <img
          src={mapImage}
          alt=""
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: 'left center',
            opacity: 0.9,
          }}
        />
      </div>

      {/* Nav */}
      <nav
        style={{
          position: 'relative',
          zIndex: 10,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '20px 48px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <img src={rentoLogo} alt="RENTO" style={{ height: 34 }} />
          <span style={{
            fontFamily: "'Sakana', sans-serif",
            fontWeight: 700,
            fontSize: 18,
            color: '#010205',
            letterSpacing: '0.08em',
          }}>
            RENTO
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={onGetStarted}
            style={{
              padding: '9px 22px',
              background: 'transparent',
              border: '1.5px solid #010205',
              borderRadius: 100,
              fontFamily: "'Montserrat', sans-serif",
              fontWeight: 600,
              fontSize: 13,
              color: '#010205',
              cursor: 'pointer',
              letterSpacing: '0.01em',
            }}
          >
            Get started
          </button>
        </div>
      </nav>

      {/* Hero text */}
      <div
        style={{
          position: 'relative',
          zIndex: 10,
          padding: '32px 48px 64px',
          maxWidth: 600,
        }}
      >
        <h1
          style={{
            fontFamily: "'Montserrat', sans-serif",
            fontSize: 'clamp(48px, 6vw, 72px)',
            fontWeight: 700,
            color: '#010205',
            lineHeight: '110%',
            letterSpacing: '-2.16px',
            margin: '0 0 20px',
          }}
        >
          Automate your rental Here&nbsp;—&nbsp;from search to negotiation.
        </h1>

        <p
          style={{
            color: '#6B6B6B',
            fontSize: 15,
            fontWeight: 400,
            margin: '0 0 40px',
            lineHeight: 1.55,
            fontFamily: "'Montserrat', sans-serif",
          }}
        >
          Data-driven search.&nbsp;&nbsp;Agent-powered negotiation.
        </p>

        {/* Partner logos */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
          <span
            style={{
              fontSize: 12,
              color: '#010205',
              fontWeight: 700,
              letterSpacing: '0.02em',
              fontFamily: "'Montserrat', sans-serif",
            }}
          >
            8M+&nbsp; house sources
          </span>
          <img src={streetEasyLogo} alt="StreetEasy" style={{ height: 22, opacity: 0.75 }} />
          <img src={craigslistLogo} alt="Craigslist" style={{ height: 22, opacity: 0.75 }} />
        </div>
      </div>
    </section>
  )
}
