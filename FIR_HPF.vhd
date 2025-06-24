library ieee;
use ieee.std_logic_1164.ALL;
use ieee.numeric_std.ALL;

entity FIR_HPF is
    Port ( CLK_50 : in std_logic;
           INPUT_ADC : in std_logic_vector (11 downto 0);
           OUTPUT_ADC : out std_logic_vector (11 downto 0));
end FIR_HPF;

architecture rtl of FIR_HPF is
    constant TAPS : integer := 37;
    signal fir_output : signed(33 downto 0) := (others => '0'); -- Perluas untuk menghindari overflow
    type signal_array is array (0 to TAPS-1) of std_logic_vector (11 downto 0);
    signal signal_buffer : signal_array;
    type coeff_array is array (0 to TAPS-1) of signed (15 downto 0);
    signal coeffs : coeff_array := (
      to_signed(-2027, 16),
      to_signed(318, 16),
      to_signed(393, 16),
      to_signed(499, 16),
      to_signed(615, 16),
      to_signed(704, 16),
      to_signed(730, 16),
      to_signed(665, 16),
      to_signed(489, 16),
      to_signed(190, 16),
      to_signed(-227, 16),
      to_signed(-745, 16),
      to_signed(-1333, 16),
      to_signed(-1949, 16),
      to_signed(-2548, 16),
      to_signed(-3077, 16),
      to_signed(-3493, 16),
      to_signed(-3759, 16),
      to_signed(28917, 16),
      to_signed(-3759, 16),
      to_signed(-3493, 16),
      to_signed(-3077, 16),
      to_signed(-2548, 16),
      to_signed(-1949, 16),
      to_signed(-1333, 16),
      to_signed(-745, 16),
      to_signed(-227, 16),
      to_signed(190, 16),
      to_signed(489, 16),
      to_signed(665, 16),
      to_signed(730, 16),
      to_signed(704, 16),
      to_signed(615, 16),
      to_signed(499, 16),
      to_signed(393, 16),
      to_signed(318, 16),
      to_signed(-2027, 16)
    );
begin
  process(CLK_50)
    variable temp_sum : signed(33 downto 0); -- Perluas variable juga
  begin
    if rising_edge(CLK_50) then
      -- Shift register
      for i in TAPS-1 downto 1 loop
        signal_buffer(i) <= signal_buffer(i-1);
      end loop;
      signal_buffer(0) <= INPUT_ADC;
      
      -- FIR calculation
      temp_sum := (others => '0');
      for i in 0 to TAPS-1 loop
        temp_sum := temp_sum + (signed('0' & signal_buffer(i)) * coeffs(i)); -- Extend to signed
      end loop;
      fir_output <= temp_sum;
    end if;
  end process;

  -- Normalisasi ke 12-bit dengan offset untuk ADC
  OUTPUT_ADC <= std_logic_vector(fir_output(28 downto 17) + to_signed(2048, 12));
end rtl;