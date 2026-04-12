import { Highlight } from "@/components/Highlight";

export function SectorAnalysis() {
  return (
    <div className="mt-20 border-t border-[#e0e0e0] pt-16">
      <h2 className="font-serif text-4xl sm:text-5xl font-bold leading-tight mb-12 text-[#222]">
        Industry Overview
        <span className="block text-2xl font-normal text-[#888] mt-2">India Hotel Market</span>
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-24 mb-16">
        <div>
          <h3 className="text-xl font-bold mb-4 font-serif">Market big. Market growing. But the race is changing.</h3>
          <p className="text-[14px] leading-[1.8] text-[#444] mb-6">
            India hotel market heading toward <Highlight quote="~$27–28 billion by 2026" refName="TO-Oct2025.pdf" citationText="Hotelivate Trends & Opportunities 2025">~$27–28 billion by 2026</Highlight>. Nationwide RevPAR jumped <Highlight quote="Nationwide RevPAR jumped 5.7% recently" refName="TO-Oct2025.pdf" citationText="Hotelivate Trends & Opportunities 2025">5.7%</Highlight> recently, and for the first time in over a decade, India's branded hotel Average Daily Rate (ADR) crossed the <Highlight quote="ADR crossed the US$100 threshold" refName="TO-Oct2025.pdf" citationText="Hotelivate Trends & Opportunities 2025">US$100 threshold</Highlight>.
          </p>
          <p className="text-[14px] leading-[1.8] text-[#444] mb-4">
            But blended averages lie. The gap between frontrunners and the midfield is widening:
          </p>
          <ul className="list-disc pl-5 space-y-3 text-[14px] leading-[1.8] text-[#444] mb-6 marker:text-[#ccc]">
            <li>
              <strong>Top 4 Urban Markets</strong> (Mumbai, Delhi, Bengaluru, Hyderabad) are carrying the sector. ADR is up ~8.3% and RevPAR up ~12.1% because demand is outpacing supply.
            </li>
            <li>
              <strong>Tier 2 & 3 Cities</strong> are seeing modest gains (RevPAR +3.2%). Why? Because supply is growing too fast (14.8% growth vs Tier 1's 3.4%).
            </li>
            <li>
              <strong>The Pipeline Shock:</strong> For the first time, India’s proposed supply crossed <Highlight quote="1,00,000 rooms" refName="TO-Oct2025.pdf" citationText="Hotelivate Trends & Opportunities 2025">1,00,000 rooms</Highlight> — a massive 58% surge planned over the next five years.
            </li>
          </ul>
        </div>
        
        <div>
          <div className="bg-[#f9f9f9] border border-[#e0e0e0] p-6 rounded-lg mb-8">
            <h4 className="font-bold text-[13px] uppercase tracking-wider mb-3 text-[#222]">The Golden Rule of Hotels: Operating Leverage</h4>
            <p className="text-[13px] leading-relaxed text-[#555]">
              A hotel has high fixed costs whether 10 or 100 rooms are full. Once occupancy crosses ~60%, almost every extra rupee of revenue drops straight to the bottom line (EBITDA). This is why the sector saw massive profit surges recently — strong demand pushed occupancies past the break-even tipping point.
            </p>
          </div>

          <h4 className="font-bold text-[15px] mb-3 text-[#222]">The 3 Things That Actually Move This Business:</h4>
          <ol className="list-decimal pl-4 space-y-3 text-[14px] leading-relaxed text-[#444] marker:font-medium marker:text-[#888]">
            <li><strong>Occupancy (Volume):</strong> How hard is the capacity running? Currently nationwide averages sit at a healthy <strong>68.0%</strong>.</li>
            <li><strong>ADR (Price):</strong> What are they charging? Premium segment rates are climbing to <strong>₹8,200–₹8,500/night</strong>.</li>
            <li><strong>New Room Supply (The Silent Killer):</strong> If 2,000 new rooms open in a city, occupancy and ADR fall even if demand is flat. Management hides this. We track it.</li>
          </ol>
        </div>
      </div>

      <hr className="border-[#e0e0e0] mb-16" />

      <div className="mb-16">
        <h3 className="text-2xl font-bold mb-6 font-serif text-[#222]">Sector Financial Snapshot & Margins</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px] border-collapse">
            <thead>
              <tr className="border-b-2 border-[#222] text-[#222]">
                <th className="py-3 px-2 font-bold">Company</th>
                <th className="py-3 px-2 font-bold">FY25 Revenue</th>
                <th className="py-3 px-2 font-bold">Op Profit</th>
                <th className="py-3 px-2 font-bold">Current OPM</th>
                <th className="py-3 px-2 font-bold text-[#888]">FY22 OPM</th>
                <th className="py-3 px-2 font-bold">The Leverage Story</th>
              </tr>
            </thead>
            <tbody>
              {[
                { name: "Lemon Tree", rev: "1,286", op: "634", opm: "49%", opmOld: "30%", story: "Volume-driven economy play maximizing its high fixed-cost leverage.", c: "LEMONTREE" },
                { name: "Chalet", rev: "1,718", op: "736", opm: "43%", opmOld: "19%", story: "Urban business hubs pushing ADRs; flow-through to margins is massive.", c: "CHALET" },
                { name: "IHCL", rev: "8,335", op: "2,769", opm: "33%", opmOld: "13%", story: "Huge revenue leap, but OPM trails peers. The silent killer? Rising F&B mix.", c: "IHCL" },
                { name: "EIH", rev: "2,743", op: "1,028", opm: "37%", opmOld: "-3%", story: "Recovered from deep COVID losses.", c: "EIH" },
                { name: "Juniper", rev: "944", op: "337", opm: "36%", opmOld: "22%", story: "Solid margins, but slight recent compression.", c: "JUNIPER" }
              ].map((row, i) => (
                <tr key={i} className="border-b border-[#e0e0e0] last:border-0 hover:bg-[#fafafa]">
                  <td className="py-3 px-2 font-semibold text-[#222]">{row.name}</td>
                  <td className="py-3 px-2 text-[#444]">₹{row.rev} Cr</td>
                  <td className="py-3 px-2 text-[#444]">₹{row.op} Cr</td>
                  <td className="py-3 px-2 font-mono font-bold text-[#059669]">
                    <Highlight quote={row.opm} refName="profit_loss.csv" company={row.c} citationText="Screener.in Profit & Loss">
                      {row.opm}
                    </Highlight>
                  </td>
                  <td className="py-3 px-2 font-mono text-[#888]">{row.opmOld}</td>
                  <td className="py-3 px-2 text-[#666] max-w-xs">{row.story}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-12 pt-12 border-t border-[#e0e0e0]">
        <div>
          <h3 className="text-xl font-bold mb-4 font-serif">Investment Opportunities</h3>
          <ul className="space-y-4 text-[14px] leading-relaxed text-[#444]">
            <li>
              <strong>The Asset-Light Pivot:</strong> Lemon Tree is the template. Moving to management contracts and franchises minimizes capital risk and drives Return on Equity (ROE) through the roof.
            </li>
            <li>
              <strong>Economy Segment Scale:</strong> Midmarket/economy penetration in India is tiny. Converting unbranded local hotels to branded flags is the highest volume opportunity.
            </li>
            <li>
              <strong>Exploiting the Tier 1 Squeeze:</strong> With 1,00,000 new keys proposed, many are rushing to Tier 2/3 cities. Real ADR growth (+8.3%) remains trapped in Tier 1 cities. Buy assets holding Tier 1 fortresses.
            </li>
          </ul>
        </div>
        
        <div>
          <h3 className="text-xl font-bold mb-4 font-serif text-[#dc2626]">Investor Risks</h3>
          <ul className="space-y-4 text-[14px] leading-relaxed text-[#444]">
            <li>
              <strong>The 1,00,000 Room Avalanche:</strong> Over the next 5 years, supply will surge 58%. If demand falters, occupancy drops below the 60% operating leverage threshold, instantly crushing the 40%+ EBITDA margins.
            </li>
            <li>
              <strong>The F&B Margin Illusion:</strong> Look past RevPAR. If a hotel's F&B revenue percentage balloons beyond 30-35%, the cost required to generate that revenue will quietly erode bottom-line profits.
            </li>
            <li>
              <strong>The Micro-Market Supply Threat:</strong> If your company makes 40% of its cash in Mumbai, and Mumbai gets <Highlight quote="1,800 new 5-star keys" refName="TO-Oct2025.pdf" citationText="Hotelivate Trends & Opportunities 2025">1,800 new rooms</Highlight>, your RevPAR is dead regardless of what India's GDP is doing.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
