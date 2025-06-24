library ieee;
use ieee.std_logic_1164.ALL;
use ieee.numeric_std.ALL;

entity FIR_HPF is
    Port ( CLK_50 : in std_logic;
           INPUT_ADC : in std_logic_vector (11 downto 0);
           OUTPUT_ADC : out std_logic_vector (11 downto 0);
           EN : in std_logic);
end FIR_HPF;

architecture rtl of FIR_HPF is
    constant TAPS : integer := 37;
    signal fir_output : std_logic_vector(27 downto 0) := (others => '0');
    type signal_array is array (0 to TAPS-1) of std_logic_vector (11 downto 0);
    signal signal_buffer : signal_array := (others => (others => '0'));
    type coeff_array is array (0 to TAPS-1) of signed(15 downto 0);
    signal coeffs : coeff_array := (
      to_signed(-2027, 16),
      to_signed(318  , 16),
      to_signed(393  , 16),
      to_signed(499  , 16),
      to_signed(615  , 16),
      to_signed(704  , 16),
      to_signed(730  , 16),
      to_signed(665  , 16),
      to_signed(489  , 16),
      to_signed(190  , 16),
      to_signed(-227 , 16),
      to_signed(-745 , 16),
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
      to_signed(-745 , 16),
      to_signed(-227 , 16),
      to_signed(190  , 16),
      to_signed(489  , 16),
      to_signed(665  , 16),
      to_signed(730  , 16),
      to_signed(704  , 16),
      to_signed(615  , 16),
      to_signed(499  , 16),
      to_signed(393  , 16),
      to_signed(318  , 16),
      to_signed(-2027, 16)
    );
begin
  process(CLK_50)
  begin
    if rising_edge(CLK_50) then
      if EN = '1' then
        -- Shift buffer
        signal_buffer(36) <= signal_buffer(35);
        signal_buffer(35) <= signal_buffer(34);
        signal_buffer(34) <= signal_buffer(33);
        signal_buffer(33) <= signal_buffer(32);
        signal_buffer(32) <= signal_buffer(31);
        signal_buffer(31) <= signal_buffer(30);
        signal_buffer(30) <= signal_buffer(29);
        signal_buffer(29) <= signal_buffer(28);
        signal_buffer(28) <= signal_buffer(27);
        signal_buffer(27) <= signal_buffer(26);
        signal_buffer(26) <= signal_buffer(25);
        signal_buffer(25) <= signal_buffer(24);
        signal_buffer(24) <= signal_buffer(23);
        signal_buffer(23) <= signal_buffer(22);
        signal_buffer(22) <= signal_buffer(21);
        signal_buffer(21) <= signal_buffer(20);
        signal_buffer(20) <= signal_buffer(19);
        signal_buffer(19) <= signal_buffer(18);
        signal_buffer(18) <= signal_buffer(17);
        signal_buffer(17) <= signal_buffer(16);
        signal_buffer(16) <= signal_buffer(15);
        signal_buffer(15) <= signal_buffer(14);
        signal_buffer(14) <= signal_buffer(13);
        signal_buffer(13) <= signal_buffer(12);
        signal_buffer(12) <= signal_buffer(11);
        signal_buffer(11) <= signal_buffer(10);
        signal_buffer(10) <= signal_buffer(9);
        signal_buffer(9) <= signal_buffer(8);
        signal_buffer(8) <= signal_buffer(7);
        signal_buffer(7) <= signal_buffer(6);
        signal_buffer(6) <= signal_buffer(5);
        signal_buffer(5) <= signal_buffer(4);
        signal_buffer(4) <= signal_buffer(3);
        signal_buffer(3) <= signal_buffer(2);
        signal_buffer(2) <= signal_buffer(1);
        signal_buffer(1) <= signal_buffer(0);
        signal_buffer(0) <= std_logic_vector(signed(INPUT_ADC) + to_signed(2048, 12));

        -- FIR calculation
        fir_output <= std_logic_vector(
                signed(signal_buffer(0)) * coeffs(0) + 
                signed(signal_buffer(1)) * coeffs(1) +
                signed(signal_buffer(2)) * coeffs(2) +
                signed(signal_buffer(3)) * coeffs(3) +
                signed(signal_buffer(4)) * coeffs(4) +
                signed(signal_buffer(5)) * coeffs(5) +
                signed(signal_buffer(6)) * coeffs(6) +
                signed(signal_buffer(7)) * coeffs(7) +
                signed(signal_buffer(8)) * coeffs(8) +
                signed(signal_buffer(9)) * coeffs(9) +
                signed(signal_buffer(10)) * coeffs(10) +
                signed(signal_buffer(11)) * coeffs(11) +
                signed(signal_buffer(12)) * coeffs(12) +
                signed(signal_buffer(13)) * coeffs(13) +
                signed(signal_buffer(14)) * coeffs(14) +
                signed(signal_buffer(15)) * coeffs(15) +
                signed(signal_buffer(16)) * coeffs(16) +
                signed(signal_buffer(17)) * coeffs(17) +
                signed(signal_buffer(18)) * coeffs(18) +
                signed(signal_buffer(19)) * coeffs(19) +
                signed(signal_buffer(20)) * coeffs(20) +
                signed(signal_buffer(21)) * coeffs(21) +
                signed(signal_buffer(22)) * coeffs(22) +
                signed(signal_buffer(23)) * coeffs(23) +
                signed(signal_buffer(24)) * coeffs(24) +
                signed(signal_buffer(25)) * coeffs(25) +
                signed(signal_buffer(26)) * coeffs(26) +
                signed(signal_buffer(27)) * coeffs(27) +
                signed(signal_buffer(28)) * coeffs(28) +
                signed(signal_buffer(29)) * coeffs(29) +
                signed(signal_buffer(30)) * coeffs(30) +
                signed(signal_buffer(31)) * coeffs(31) +
                signed(signal_buffer(32)) * coeffs(32) +
                signed(signal_buffer(33)) * coeffs(33) +
                signed(signal_buffer(34)) * coeffs(34) +
                signed(signal_buffer(35)) * coeffs(35) +
                signed(signal_buffer(36)) * coeffs(36));
      end if;     
    end if;
  end process;

  OUTPUT_ADC <= std_logic_vector(signed(fir_output(26 downto 15)) + 2048);
end rtl;